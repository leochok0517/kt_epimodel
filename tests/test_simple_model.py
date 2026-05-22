"""Unit tests for kt_epimodel.calibration.simple_model."""

from __future__ import annotations

import functools

import numpy as np
import pytest

from kt_epimodel.calibration.simple_model import (
    build_aggregated_inputs,
    estimate_initial_infected_from_ili,
    simulate_aggregated,
)
from kt_epimodel.model.parameters import ModelParameters


@functools.lru_cache(maxsize=1)
def _cached_inputs() -> dict:
    return build_aggregated_inputs()


# ---------- build_aggregated_inputs ----------

def test_build_inputs_shapes() -> None:
    inp = _cached_inputs()
    assert inp["pop_15"].shape == (15, 1)
    assert inp["rho"].shape == (1, 15)
    assert inp["admdong_codes"] == ["SUDOGWON"]


def test_build_inputs_pop_aggregated() -> None:
    """수도권 인구 25M 수준."""
    inp = _cached_inputs()
    assert 20_000_000 < inp["pop_15"].sum() < 30_000_000


def test_build_inputs_mobility_all_identity() -> None:
    inp = _cached_inputs()
    for ch in ("home", "school", "work", "other"):
        M = inp["mobility"][ch]
        assert M.shape == (15, 1, 1)
        np.testing.assert_array_equal(M, np.ones((15, 1, 1)))


def test_build_inputs_matrices_present() -> None:
    inp = _cached_inputs()
    for key in ("C_home", "C_work", "C_school", "C_other"):
        assert key in inp["matrices"]
        assert inp["matrices"][key].shape == (15, 15)


def test_rho_under_15_zero() -> None:
    """0-4, 5-9, 10-14 (idx 0,1,2) = 0 (no employment data)."""
    inp = _cached_inputs()
    np.testing.assert_array_equal(inp["rho"][0, 0:3], 0.0)


def test_rho_workers_reasonable() -> None:
    """30-34 (idx 6) 고용률 ~ 0.8."""
    inp = _cached_inputs()
    assert 0.7 < inp["rho"][0, 6] < 0.85


def test_rho_70plus_low() -> None:
    inp = _cached_inputs()
    assert inp["rho"][0, 14] < 0.2


def test_rho_in_unit_interval() -> None:
    inp = _cached_inputs()
    assert (inp["rho"] >= 0).all()
    assert (inp["rho"] <= 1).all()


# ---------- simulate_aggregated ----------

def test_simulate_runs() -> None:
    inp = _cached_inputs()
    r = simulate_aggregated(ModelParameters(), inp, seed_total=100, t_span=(0, 10))
    assert r.success


def test_simulate_conservation() -> None:
    inp = _cached_inputs()
    r = simulate_aggregated(ModelParameters(), inp, seed_total=100, t_span=(0, 30))
    target = inp["pop_15"].sum()
    totals = r.states.sum(axis=(1, 2, 3))
    np.testing.assert_allclose(totals, target, rtol=1e-5)


def test_simulate_employment_auto_injected() -> None:
    """employment=None 인 ModelParameters → 자동 주입."""
    inp = _cached_inputs()
    p = ModelParameters()
    assert p.employment is None
    # 실행 후 새 params 는 employment 채워짐
    _ = simulate_aggregated(p, inp, seed_total=100, t_span=(0, 5))
    # p 자체는 immutable — simulate 가 내부에서 새 인스턴스 생성


def test_simulate_seed_total_applied() -> None:
    inp = _cached_inputs()
    r = simulate_aggregated(ModelParameters(), inp, seed_total=500, t_span=(0, 1))
    # 초기 I 총합 = 500
    np.testing.assert_allclose(r.states[0, 3].sum(), 500, atol=1e-6)


# ---------- estimate_initial_infected_from_ili ----------

def test_estimate_seed_returns_15() -> None:
    pop = np.full(15, 1_000_000.0)
    seed = estimate_initial_infected_from_ili("2019-2020", pop)
    assert seed.shape == (15,)


def test_estimate_seed_nonnegative() -> None:
    pop = np.full(15, 1_000_000.0)
    seed = estimate_initial_infected_from_ili("2019-2020", pop)
    assert (seed >= 0).all()


def test_estimate_seed_proportional_to_pop() -> None:
    """인구 2배 → seed 2배 (다른 모든 조건 동일)."""
    pop1 = np.full(15, 1_000_000.0)
    pop2 = pop1 * 2
    s1 = estimate_initial_infected_from_ili("2019-2020", pop1)
    s2 = estimate_initial_infected_from_ili("2019-2020", pop2)
    np.testing.assert_allclose(s2, 2 * s1, rtol=1e-10)


def test_estimate_seed_gamma_report_assumed_2_halves() -> None:
    pop = np.full(15, 1_000_000.0)
    s1 = estimate_initial_infected_from_ili("2019-2020", pop, gamma_report_assumed=1.0)
    s2 = estimate_initial_infected_from_ili("2019-2020", pop, gamma_report_assumed=2.0)
    np.testing.assert_allclose(s2, s1 / 2.0, rtol=1e-12)


def test_estimate_seed_gamma_report_assumed_3_thirds() -> None:
    pop = np.full(15, 1_000_000.0)
    s1 = estimate_initial_infected_from_ili("2019-2020", pop, gamma_report_assumed=1.0)
    s3 = estimate_initial_infected_from_ili("2019-2020", pop, gamma_report_assumed=3.0)
    np.testing.assert_allclose(s3, s1 / 3.0, rtol=1e-12)


def test_estimate_seed_default_gamma_is_2() -> None:
    pop = np.full(15, 1_000_000.0)
    s_default = estimate_initial_infected_from_ili("2019-2020", pop)
    s_explicit = estimate_initial_infected_from_ili("2019-2020", pop, gamma_report_assumed=2.0)
    np.testing.assert_array_equal(s_default, s_explicit)


def test_estimate_seed_invalid_gamma_raises() -> None:
    import pytest as _pt
    with _pt.raises(ValueError):
        estimate_initial_infected_from_ili(
            "2019-2020", np.full(15, 1_000_000.0), gamma_report_assumed=0.0,
        )
    with _pt.raises(ValueError):
        estimate_initial_infected_from_ili(
            "2019-2020", np.full(15, 1_000_000.0), gamma_report_assumed=-1.0,
        )


def test_estimate_seed_total_positive() -> None:
    inp = _cached_inputs()
    pop = inp["pop_15"].flatten()
    seed = estimate_initial_infected_from_ili("2019-2020", pop)
    assert seed.sum() > 0


# ---------- simulate with seed_by_age ----------

def test_simulate_with_seed_by_age() -> None:
    inp = _cached_inputs()
    seed = np.full(15, 100.0)
    r = simulate_aggregated(
        ModelParameters(), inp, seed_by_age=seed, t_span=(0, 5),
    )
    assert r.success
    # 초기 I 합 ≈ 1500 (15 × 100)
    np.testing.assert_allclose(r.states[0, 3].sum(), 1500.0, rtol=1e-9)


def test_simulate_seed_by_age_overrides_seed_total() -> None:
    """seed_by_age 제공 시 seed_total 무시."""
    inp = _cached_inputs()
    seed = np.full(15, 10.0)
    r = simulate_aggregated(
        ModelParameters(), inp,
        seed_total=999999,        # 무시되어야
        seed_by_age=seed, t_span=(0, 1),
    )
    np.testing.assert_allclose(r.states[0, 3].sum(), 150.0, rtol=1e-9)


def test_simulate_seed_by_age_e_factor() -> None:
    """E0 = I0 · seed_e_factor."""
    inp = _cached_inputs()
    seed = np.full(15, 100.0)
    r = simulate_aggregated(
        ModelParameters(), inp,
        seed_by_age=seed, seed_e_factor=0.5, t_span=(0, 1),
    )
    # I = 100, E = 50 per age → total: I=1500, E=750
    np.testing.assert_allclose(r.states[0, 3].sum(), 1500.0, rtol=1e-9)
    np.testing.assert_allclose(r.states[0, 2].sum(), 750.0, rtol=1e-9)


def test_simulate_initial_immunity() -> None:
    inp = _cached_inputs()
    r = simulate_aggregated(
        ModelParameters(), inp, seed_total=0, initial_immunity=0.2, t_span=(0, 1),
    )
    R0 = r.states[0, 4].sum()
    pop = inp["pop_15"].sum()
    assert R0 == pytest.approx(0.2 * pop, rel=1e-6)
