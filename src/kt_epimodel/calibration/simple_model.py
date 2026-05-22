"""Aggregated (1-admdong) 모델 — calibration 인프라.

행정동 1,154 → 단일 admdong 으로 합산 (수도권 전체).
mobility 는 모두 identity (15, 1, 1).
ρ 는 시도별 인구 가중 평균 → (1, 15).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from kt_data import (
    load_contact_matrices,
    load_employment_rate,
    load_population_15groups,
)
from kt_data.data.load_population import get_population_matrix

from kt_epimodel.model.compartments import (
    IDX_E,
    IDX_I,
    IDX_R,
    IDX_S,
    IDX_V,
    N_COMPARTMENTS,
    initial_state,
)
from kt_epimodel.model.parameters import (
    EmploymentParameters,
    ModelParameters,
)
from kt_epimodel.simulation.solver import SimulationResult, run_simulation


def build_aggregated_inputs() -> dict[str, Any]:
    """수도권 합산 inputs (1 admdong, 15 ages)."""
    df_pop = load_population_15groups()
    N_mat, _codes, _ = get_population_matrix(df_pop)
    pop_aggregated = N_mat.sum(axis=0).reshape(15, 1).astype(np.float64)

    matrices = load_contact_matrices()

    mobility_eye = np.ones((15, 1, 1), dtype=np.float64)
    mobility = {
        "home":   mobility_eye.copy(),
        "school": mobility_eye.copy(),
        "work":   mobility_eye.copy(),
        "other":  mobility_eye.copy(),
    }

    # ρ: 수도권 3 시도 인구 가중 평균.
    # load_population 의 sido_nm 은 풀네임 ("서울특별시"), employment 는 약칭 ("서울").
    df_emp = load_employment_rate()
    sudogwon_short = ["서울", "경기", "인천"]
    sudogwon_full = {"서울": "서울특별시", "경기": "경기도", "인천": "인천광역시"}
    sudogwon_emp = df_emp.filter(pl.col("sido_nm").is_in(sudogwon_short))

    sido_pops: dict[str, float] = {}
    for short in sudogwon_short:
        full = sudogwon_full[short]
        sido_pops[short] = float(
            df_pop.filter(pl.col("sido_nm") == full).get_column("pop").sum()
        )
    total_sudogwon_pop = sum(sido_pops.values())
    if total_sudogwon_pop == 0:
        raise RuntimeError("Sudogwon population zero — check load_population_15groups")

    rho_by_age = np.zeros(15, dtype=np.float64)
    for row in sudogwon_emp.iter_rows(named=True):
        a = int(row["age_idx"])
        if 0 <= a < 15:
            w = sido_pops[row["sido_nm"]] / total_sudogwon_pop
            rho_by_age[a] += float(row["employment_rate"]) * w
    rho = rho_by_age.reshape(1, 15)

    return {
        "pop_15": pop_aggregated,
        "mobility": mobility,
        "matrices": matrices,
        "rho": rho,
        "admdong_codes": ["SUDOGWON"],
    }


def estimate_initial_infected_from_ili(
    season: str,
    pop_15: np.ndarray,
    week_zero_average_n: int = 3,
    gamma_report_assumed: float = 2.0,
) -> np.ndarray:
    """ILI 시즌 초반 baseline 으로 NIMS 15군 초기 I 추정.

    수식: I = ILI · pop / 1000 / γ_report_assumed.

    Args:
        season: '2019-2020' 등.
        pop_15: (15,) 또는 (15, n_admdong) — 합산되어 사용.
        week_zero_average_n: 처음 N 주 평균 (단일 주 노이즈 회피).
        gamma_report_assumed: ILI → I 변환 시 가정한 보고율.
            큰 값일수록 seed 작음. default 2.0 (외래 분모 보정 + 보수적).

    Returns:
        (15,) — 연령별 초기 I 인원수.
    """
    if gamma_report_assumed <= 0:
        raise ValueError(
            f"gamma_report_assumed must be > 0, got {gamma_report_assumed}"
        )
    from kt_data.data.load_ili import (
        ILI_AGE_GROUPS,
        ILI_GROUP_TO_NIMS_WEIGHTED,
        load_ili_by_age,
    )

    pop_arr = np.asarray(pop_15, dtype=np.float64)
    if pop_arr.ndim == 2:
        pop_total_15 = pop_arr.sum(axis=1) if pop_arr.shape[0] == 15 else pop_arr.flatten()
    else:
        pop_total_15 = pop_arr
    if pop_total_15.shape != (15,):
        raise ValueError(f"pop_15 must reduce to (15,), got {pop_total_15.shape}")

    ili_baseline: dict[str, float] = {}
    for ag in ILI_AGE_GROUPS:
        df = load_ili_by_age(ag)
        sub = (
            df.filter((pl.col("season") == season) & pl.col("is_valid_week"))
            .sort("week_in_season")
        )
        rates = sub.get_column("ili_rate").to_numpy()
        early = rates[: int(week_zero_average_n)]
        valid = ~np.isnan(early)
        ili_baseline[ag] = float(np.nanmean(early[valid])) if valid.any() else 0.0

    I_initial_15 = np.zeros(15, dtype=np.float64)
    for ag, weights in ILI_GROUP_TO_NIMS_WEIGHTED.items():
        total_weighted_pop = sum(w * float(pop_total_15[idx]) for idx, w in weights.items())
        if total_weighted_pop < 1e-10:
            continue
        I_group = (
            ili_baseline[ag] * total_weighted_pop / 1000.0 / gamma_report_assumed
        )
        for nims_idx, w in weights.items():
            share = (w * float(pop_total_15[nims_idx])) / total_weighted_pop
            I_initial_15[nims_idx] += I_group * share
    return I_initial_15


def _build_initial_state_with_age_seed(
    pop_15: np.ndarray,
    seed_by_age: np.ndarray,
    seed_e_factor: float,
    initial_immunity: float,
    initial_vaccinated_fraction: float,
) -> np.ndarray:
    """연령별 seed 로 SEIRV 초기 state 직접 구성.

    상태 텐서: (5, 15, n_admdong). 행정동 분배는 인구 비례.
    """
    pop_arr = np.asarray(pop_15, dtype=np.float64)
    if pop_arr.ndim == 1:
        pop_2d = pop_arr.reshape(15, 1)
    else:
        pop_2d = pop_arr
    n_age, n_adm = pop_2d.shape

    seed = np.asarray(seed_by_age, dtype=np.float64)
    if seed.shape != (15,):
        raise ValueError(f"seed_by_age must be (15,), got {seed.shape}")
    if (seed < 0).any():
        raise ValueError("seed_by_age must be nonneg")

    state = np.zeros((N_COMPARTMENTS, n_age, n_adm), dtype=np.float64)
    for a in range(n_age):
        row = pop_2d[a]
        n_a = row.sum()
        if n_a <= 0:
            continue
        share = row / n_a

        i_seed = float(seed[a])
        e_seed = i_seed * float(seed_e_factor)
        r_init = float(initial_immunity) * n_a
        v_init = float(initial_vaccinated_fraction) * n_a
        s_init = n_a - i_seed - e_seed - r_init - v_init
        if s_init < 0:
            # 과도한 seed/immunity 시 i+e 비율 축소 (R, V 유지)
            avail = max(n_a - r_init - v_init, 0.0)
            total_ie = i_seed + e_seed
            if total_ie > 0:
                scale = avail / total_ie
                i_seed *= scale
                e_seed *= scale
                s_init = 0.0
            else:
                s_init = 0.0

        state[IDX_S, a] = s_init * share
        state[IDX_V, a] = v_init * share
        state[IDX_E, a] = e_seed * share
        state[IDX_I, a] = i_seed * share
        state[IDX_R, a] = r_init * share

    return state


def simulate_aggregated(
    params: ModelParameters,
    inputs: dict[str, Any],
    seed_total: float = 100.0,
    seed_by_age: np.ndarray | None = None,
    seed_e_factor: float = 0.5,
    initial_immunity: float = 0.0,
    initial_vaccinated_fraction: float = 0.0,
    t_span: tuple[float, float] = (0.0, 224.0),
    day_in_season_offset: float = 0.0,
) -> SimulationResult:
    """집계 모델 시뮬레이션.

    seed_by_age 제공 시: 연령별 seed 직접 사용 (seed_total 무시).
                        E0 = I0 · seed_e_factor.
    seed_by_age=None: 기존 동작 (seed_total 분배).
    """
    if params.employment is None:
        params = params.with_employment(EmploymentParameters(rho=inputs["rho"]))

    if seed_by_age is not None:
        state = _build_initial_state_with_age_seed(
            inputs["pop_15"], seed_by_age, seed_e_factor,
            initial_immunity, initial_vaccinated_fraction,
        )
    else:
        state = initial_state(
            inputs["pop_15"],
            seed_per_admdong=seed_total,
            seed_age_distribution="population_weighted",
            initial_immunity=initial_immunity,
            initial_vaccinated_fraction=initial_vaccinated_fraction,
        )

    return run_simulation(
        state,
        inputs["mobility"],
        inputs["matrices"],
        inputs["pop_15"],
        params,
        t_span=t_span,
        day_in_season_offset=day_in_season_offset,
    )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    AGE_LABELS_DEMO = [
        "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39",
        "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70+",
    ]
    inputs_demo = build_aggregated_inputs()
    pop_demo = inputs_demo["pop_15"].flatten()

    print("=== Seed (2019-2020) by gamma_report_assumed ===")
    for gr in (1.0, 1.5, 2.0, 3.0, 5.0):
        s = estimate_initial_infected_from_ili(
            "2019-2020", pop_demo, gamma_report_assumed=gr,
        )
        print(f"  γ_report_assumed = {gr:>4}: total seed = {s.sum():>10,.0f}")

    print("\n=== Default (γ_report_assumed=2.0) — 2019-2020 ===")
    seed = estimate_initial_infected_from_ili("2019-2020", pop_demo)
    for a, lab in enumerate(AGE_LABELS_DEMO):
        pct = seed[a] / pop_demo[a] * 100 if pop_demo[a] > 0 else 0.0
        print(f"    [{a:>2}] {lab:>5}: {seed[a]:>10,.0f}  ({pct:.4f}% pop)")
    print(f"    Total: {seed.sum():,.0f}")
    print()

    inputs = build_aggregated_inputs()
    print("=== Aggregated inputs ===")
    print(f"pop_15 shape: {inputs['pop_15'].shape}, total: {inputs['pop_15'].sum():,.0f}")
    print(f"rho shape:    {inputs['rho'].shape}")
    print("rho by age (mean):")
    AGE_LABELS = [
        "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39",
        "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70+",
    ]
    for a, label in enumerate(AGE_LABELS):
        print(f"  [{a:>2}] {label:>5}: {inputs['rho'][0, a]:.3f}")

    params = ModelParameters()
    result = simulate_aggregated(params, inputs, seed_total=100, t_span=(0, 30))
    print(f"\n=== Simulation 30 days ===")
    print(f"success: {result.success}")
    totals = result.total_by_compartment()
    print(f"day 0:  S={totals[0, IDX_S]:>12,.0f}, V={totals[0, IDX_V]:>10,.0f}, "
          f"I={totals[0, IDX_I]:>8,.0f}, R={totals[0, IDX_R]:>10,.0f}")
    print(f"day 30: S={totals[-1, IDX_S]:>12,.0f}, V={totals[-1, IDX_V]:>10,.0f}, "
          f"I={totals[-1, IDX_I]:>8,.0f}, R={totals[-1, IDX_R]:>10,.0f}")
    print(f"보존: Δ={totals.sum(axis=1).max() - totals.sum(axis=1).min():.3e}")
