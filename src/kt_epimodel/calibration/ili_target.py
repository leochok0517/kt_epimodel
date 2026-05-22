"""ILI calibration target (Stage 3-1).

질병관리청 ILI 주별 분율을 모델 fit target 으로 변환.
모델 일일 incidence → 주별 ILI 분율 변환 + Poisson log-likelihood.
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import polars as pl

from kt_data.data.load_ili import load_ili_seasons

N_WEEKS: int = 52


def load_ili_target(
    season: str,
    interpolate_nan: bool = True,
    df: pl.DataFrame | None = None,
    first_peak_only: bool = False,
    first_peak_end_week: int = 26,
) -> dict:
    """한 시즌 ILI 시계열 → calibration용 dict.

    Args:
        season: '2018-2019' 등.
        interpolate_nan: 시즌 내부 NaN 선형 보간.
        df: load_ili_seasons() 결과 사전 주입 (없으면 자동 로드).
        first_peak_only: True 면 첫 봉우리 (week < first_peak_end_week) 만 weight 1.
        first_peak_end_week: 첫 봉우리 종료 주차 (기본 26 ≈ 시즌 +6개월, 3월 초).

    Returns:
        dict {season, week_in_season, iso_week, ili_rate, is_valid, weights, n_weeks}.
        weights: NLL 가중치 — default 는 is_valid float, first_peak_only=True 면 후반부 0.
    """
    if df is None:
        df = load_ili_seasons()
    sub = (
        df.filter((pl.col("season") == season) & pl.col("is_valid_week"))
        .sort("week_in_season")
    )
    if sub.height == 0:
        raise ValueError(f"unknown season: {season!r}")

    weeks = sub.get_column("week_in_season").to_numpy()
    iso = sub.get_column("iso_week").to_numpy()
    rates = sub.get_column("ili_rate").to_numpy()

    nan_mask = np.isnan(rates)
    if interpolate_nan and nan_mask.any() and (~nan_mask).any():
        rates = rates.copy()
        valid_idx = np.where(~nan_mask)[0]
        rates[nan_mask] = np.interp(np.where(nan_mask)[0], valid_idx, rates[valid_idx])

    is_valid = ~np.isnan(rates)
    weights = is_valid.astype(np.float64)
    if first_peak_only:
        weights[weeks >= first_peak_end_week] = 0.0

    return {
        "season": season,
        "week_in_season": weeks,
        "iso_week": iso,
        "ili_rate": rates,
        "is_valid": is_valid,
        "weights": weights,
        "n_weeks": int(len(weeks)),
    }


def season_start_date(season: str) -> int:
    """시즌명 → ISO 36주 월요일 yyyymmdd.

    예: '2018-2019' → 20180903.
    """
    start_year = int(season.split("-")[0])
    d = _dt.date.fromisocalendar(start_year, 36, 1)
    return d.year * 10000 + d.month * 100 + d.day


def simulation_to_ili(
    daily_incidence: np.ndarray,
    population: float,
    gamma_report: float,
    n_weeks: int = N_WEEKS,
) -> np.ndarray:
    """시뮬레이션 일일 신규감염 → 주별 ILI (per 1000).

    Args:
        daily_incidence: (n_days,) 또는 (n_days, ...) — ... 차원은 합산.
        population: 분모 인구 (scalar).
        gamma_report: 보고율 (0..1).
        n_weeks: 출력 주차 수 (기본 52). 부족하면 0 패딩, 넘치면 절단.
    """
    arr = np.asarray(daily_incidence, dtype=np.float64)
    if arr.ndim > 1:
        daily_total = arr.reshape(arr.shape[0], -1).sum(axis=1)
    else:
        daily_total = arr

    n_complete = len(daily_total) // 7
    weekly = daily_total[: n_complete * 7].reshape(-1, 7).sum(axis=1)
    ili = gamma_report * weekly / population * 1000.0

    if len(ili) >= n_weeks:
        return ili[:n_weeks]
    return np.concatenate([ili, np.zeros(n_weeks - len(ili))])


def load_ili_target_by_age(
    season: str,
    first_peak_only: bool = False,
    first_peak_end_week: int = 26,
    interpolate_nan: bool = True,
) -> dict:
    """7 연령 그룹 ILI target.

    Returns:
        {'season', 'age_groups', 'ili_rates', 'weights', 'is_valid',
         'week_in_season', 'n_weeks'}
        ili_rates/weights/is_valid 는 {age_group: (52,)} dict.
    """
    from kt_data.data.load_ili import ILI_AGE_GROUPS, load_ili_by_age

    result: dict = {
        "season": season,
        "age_groups": list(ILI_AGE_GROUPS),
        "ili_rates": {},
        "weights": {},
        "is_valid": {},
        "week_in_season": None,
        "n_weeks": N_WEEKS,
    }

    for ag in ILI_AGE_GROUPS:
        df = load_ili_by_age(ag)
        sub = (
            df.filter((pl.col("season") == season) & pl.col("is_valid_week"))
            .sort("week_in_season")
        )
        if sub.height == 0:
            raise ValueError(f"unknown season for age group {ag!r}: {season!r}")

        weeks = sub.get_column("week_in_season").to_numpy()
        rates = sub.get_column("ili_rate").to_numpy()
        nan_mask = np.isnan(rates)
        if interpolate_nan and nan_mask.any() and (~nan_mask).any():
            rates = rates.copy()
            valid_idx = np.where(~nan_mask)[0]
            rates[nan_mask] = np.interp(np.where(nan_mask)[0], valid_idx, rates[valid_idx])

        is_valid = ~np.isnan(rates)
        weights = is_valid.astype(np.float64)
        if first_peak_only:
            weights[weeks >= first_peak_end_week] = 0.0

        result["ili_rates"][ag] = rates
        result["weights"][ag] = weights
        result["is_valid"][ag] = is_valid
        if result["week_in_season"] is None:
            result["week_in_season"] = weeks

    return result


def simulation_to_ili_by_age(
    daily_incidence_by_age: np.ndarray,
    pop_15: np.ndarray,
    gamma_report: float,
    n_weeks: int = N_WEEKS,
    use_weighted: bool = True,
) -> dict[str, np.ndarray]:
    """모델 출력 → 7 연령 그룹 주별 ILI.

    Args:
        daily_incidence_by_age: (n_days, 15) — 연령별 일일 신규 감염.
        pop_15: (15,) 또는 (15, 1) 합산 인구.
        gamma_report: 보고율.
        n_weeks: 출력 주차 수.
        use_weighted: True 면 ILI_GROUP_TO_NIMS_WEIGHTED (정확 인구비례),
                      False 면 ILI_GROUP_TO_NIMS (단순 합산, legacy).

    Returns:
        {age_group: (n_weeks,) ILI rate per 1000}
    """
    from kt_data.data.load_ili import (
        ILI_GROUP_TO_NIMS,
        ILI_GROUP_TO_NIMS_WEIGHTED,
    )

    arr = np.asarray(daily_incidence_by_age, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 15:
        raise ValueError(f"daily_incidence_by_age must be (n_days, 15), got {arr.shape}")

    pop = np.asarray(pop_15, dtype=np.float64).reshape(-1)
    if pop.size != 15:
        pop = np.asarray(pop_15, dtype=np.float64)
        if pop.ndim == 2 and pop.shape[0] == 15:
            pop = pop.sum(axis=1)
        else:
            raise ValueError(f"pop_15 must reduce to 15 ages, got shape {pop_15.shape}")

    n_days = arr.shape[0]
    n_complete = n_days // 7
    weekly = arr[: n_complete * 7].reshape(n_complete, 7, 15).sum(axis=1)   # (n_w, 15)

    def _pad(ili: np.ndarray) -> np.ndarray:
        if len(ili) >= n_weeks:
            return ili[:n_weeks]
        return np.concatenate([ili, np.zeros(n_weeks - len(ili))])

    out: dict[str, np.ndarray] = {}
    if use_weighted:
        for ag, weights in ILI_GROUP_TO_NIMS_WEIGHTED.items():
            group_inc = np.zeros(weekly.shape[0])
            group_pop = 0.0
            for nims_idx, w in weights.items():
                group_inc += w * weekly[:, nims_idx]
                group_pop += w * float(pop[nims_idx])
            if group_pop > 1e-10:
                ili = gamma_report * group_inc / group_pop * 1000.0
            else:
                ili = np.zeros_like(group_inc)
            out[ag] = _pad(ili)
    else:
        for ag, nims_idx in ILI_GROUP_TO_NIMS.items():
            group_inc = weekly[:, nims_idx].sum(axis=1)
            group_pop = float(pop[nims_idx].sum())
            if group_pop > 1e-10:
                ili = gamma_report * group_inc / group_pop * 1000.0
            else:
                ili = np.zeros_like(group_inc)
            out[ag] = _pad(ili)
    return out


def poisson_log_likelihood(
    observed: np.ndarray,
    predicted: np.ndarray,
    is_valid: np.ndarray | None = None,
    weights: np.ndarray | None = None,
    min_rate: float = 1e-6,
) -> float:
    """Weighted Poisson NLL = Σ w_i [y_pred − y_obs · log(y_pred)].

    Args:
        weights: (n_weeks,) 가중치. None 이면 1.0. weight=0 인 주는 NLL 기여 0.
    """
    observed = np.asarray(observed, dtype=np.float64)
    predicted = np.asarray(predicted, dtype=np.float64)
    if observed.shape != predicted.shape:
        raise ValueError(
            f"shape mismatch: observed {observed.shape} vs predicted {predicted.shape}"
        )

    mask = np.ones_like(observed, dtype=bool) if is_valid is None else is_valid.astype(bool)
    mask &= ~np.isnan(observed)
    mask &= ~np.isnan(predicted)

    if weights is None:
        w_arr = np.ones_like(observed, dtype=np.float64)
    else:
        w_arr = np.asarray(weights, dtype=np.float64)
        if w_arr.shape != observed.shape:
            raise ValueError(
                f"weights shape {w_arr.shape} != observed {observed.shape}"
            )
        mask &= w_arr > 0

    obs = observed[mask]
    pred = np.maximum(predicted[mask], min_rate)
    w = w_arr[mask]
    if obs.size == 0:
        return float("inf")
    return float(np.sum(w * (pred - obs * np.log(pred))))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from pathlib import Path

    import matplotlib.pyplot as plt

    seasons = ["2018-2019", "2019-2020", "2022-2023"]
    df = load_ili_seasons()

    for s in seasons:
        data = load_ili_target(s, df=df)
        start = season_start_date(s)
        peak_idx = int(np.nanargmax(data["ili_rate"]))
        print(f"\n=== {s} ===")
        print(f"  시작 yyyymmdd:   {start}")
        print(f"  n_weeks:         {data['n_weeks']}")
        print(f"  valid weeks:     {int(data['is_valid'].sum())}")
        print(f"  rate range:      {np.nanmin(data['ili_rate']):.2f} ~ "
              f"{np.nanmax(data['ili_rate']):.2f}")
        print(f"  peak (week_in):  {int(data['week_in_season'][peak_idx])}")

    fig, ax = plt.subplots(figsize=(12, 5))
    for s in seasons:
        d = load_ili_target(s, df=df)
        ax.plot(d["week_in_season"], d["ili_rate"], marker="o", label=s)
    ax.set_xlabel("Week in season")
    ax.set_ylabel("ILI rate (per 1000)")
    ax.set_title("ILI calibration targets")
    ax.legend(); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out = Path("outputs/ili_targets.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"\nsaved {out}")

    target = load_ili_target("2018-2019", df=df)["ili_rate"]
    nll_perfect  = poisson_log_likelihood(target, target.copy())
    nll_constant = poisson_log_likelihood(target, np.full_like(target, np.nanmean(target)))
    nll_zero     = poisson_log_likelihood(target, np.full_like(target, 1e-3))
    print("\n=== Loss 검증 ===")
    print(f"  NLL perfect:      {nll_perfect:.2f}")
    print(f"  NLL constant mean:{nll_constant:.2f}")
    print(f"  NLL near zero:    {nll_zero:.2f}")
    print("  (perfect < constant < zero 기대)")

    print("\n" + "=" * 70)
    print("First-peak-only target 데모")
    print("=" * 70)
    for season in ("2019-2020", "2018-2019"):
        t_full = load_ili_target(season, df=df, first_peak_only=False)
        t_first = load_ili_target(season, df=df, first_peak_only=True, first_peak_end_week=26)
        obs = t_full["ili_rate"]
        print(f"\n--- {season} ---")
        print(f"  full weights sum:        {t_full['weights'].sum():.0f} ({(t_full['weights'] > 0).sum()} weeks)")
        print(f"  first-peak weights sum:  {t_first['weights'].sum():.0f} ({(t_first['weights'] > 0).sum()} weeks)")
        # top 3 peaks
        order = np.argsort(obs)[::-1][:3]
        print(f"  top 3 ILI weeks: {[(int(i), float(obs[i])) for i in order]}")
        # zero-prediction NLL 비교
        pred_zero = np.full_like(obs, 1e-3)
        nll_full = poisson_log_likelihood(obs, pred_zero, t_full["is_valid"], weights=t_full["weights"])
        nll_first = poisson_log_likelihood(obs, pred_zero, t_first["is_valid"], weights=t_first["weights"])
        print(f"  NLL (zero pred) full / first-peak: {nll_full:.2f} / {nll_first:.2f}")
