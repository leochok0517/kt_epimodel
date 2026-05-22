"""Unit tests for kt_epimodel.simulation.solver (Step E — SEIRV)."""

from __future__ import annotations

import time

import numpy as np
import pytest

from kt_epimodel.model.compartments import (
    IDX_E,
    IDX_I,
    IDX_R,
    IDX_S,
    IDX_V,
    N_AGE,
    initial_state,
)
from kt_epimodel.model.mobility_tensor import (
    build_M_from_kt_array,
    build_M_home,
    build_M_school,
)
from kt_epimodel.model.parameters import (
    CalibrationParameters,
    EmploymentParameters,
    ModelParameters,
    VaccinationParameters,
)
from kt_epimodel.simulation.solver import (
    SimulationResult,
    run_simulation,
)

N_ADM = 4


def _setup(beta: float = 0.3, seed_per: float = 50.0, VE: float = 0.5) -> dict:
    rng = np.random.default_rng(0)
    pop = rng.integers(500, 2000, size=(N_AGE, N_ADM)).astype(np.float64)
    pi_kt = rng.uniform(1.0, 20.0, size=(N_ADM, N_ADM, 7, 24))
    mobility = {
        "home":   build_M_home(N_ADM),
        "school": build_M_school(N_ADM),
        "work":   build_M_from_kt_array(pi_kt, "work"),
        "other":  build_M_from_kt_array(pi_kt, "other"),
    }
    matrices = {k: np.full((N_AGE, N_AGE), 0.5) for k in ("C_home", "C_work", "C_school", "C_other")}

    rho = np.zeros((N_ADM, N_AGE))
    rho[:, 4:14] = 0.7
    emp = EmploymentParameters(rho=rho)

    params = ModelParameters(
        calibration=CalibrationParameters(
            beta_h=beta, beta_w=beta, beta_s=beta, beta_o=beta,
            phi=np.ones(N_AGE), gamma_report=0.5,
        ),
        vaccination=VaccinationParameters(VE=VE),
    ).with_employment(emp)

    state = initial_state(pop, seed_per_admdong=seed_per)
    return {
        "pop": pop, "mobility": mobility, "matrices": matrices,
        "state": state, "params": params,
    }


# ---------- basic ----------

def test_run_simulation_success() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    assert r.success
    assert isinstance(r, SimulationResult)


def test_states_shape() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    assert r.states.shape == (len(r.t), 5, N_AGE, N_ADM)


def test_initial_state_at_t0() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    np.testing.assert_allclose(r.states[0], s["state"], rtol=1e-10)


# ---------- conservation & sign ----------

def test_population_conserved_throughout() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 30))
    total = r.states.sum(axis=(1, 2, 3))
    np.testing.assert_allclose(total, s["pop"].sum(), rtol=1e-5)


def test_no_negative_states() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 30))
    assert (r.states >= -1e-5).all()


def test_S_monotonically_decreases() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 30))
    S_total = r.states[:, IDX_S].sum(axis=(1, 2))
    diffs = np.diff(S_total)
    assert (diffs <= 1e-5).all()


def test_R_monotonically_increases() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 30))
    R_total = r.states[:, IDX_R].sum(axis=(1, 2))
    diffs = np.diff(R_total)
    assert (diffs >= -1e-5).all()


def test_V_grows_over_vaccination_period() -> None:
    """30일 시뮬레이션 동안 V 증가 (시즌 시작 무렵 백신 유입)."""
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 30))
    V_total = r.states[:, IDX_V].sum(axis=(1, 2))
    assert V_total[-1] > V_total[0]


# ---------- edge cases ----------

def test_zero_infectious_stays_zero() -> None:
    s = _setup(seed_per=0.0)
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 30))
    np.testing.assert_allclose(r.states[:, IDX_I], 0.0, atol=1e-9)
    np.testing.assert_allclose(r.states[:, IDX_E], 0.0, atol=1e-9)
    np.testing.assert_allclose(r.states[:, IDX_R], 0.0, atol=1e-9)


def test_tiny_beta_negligible_S_to_E() -> None:
    s = _setup(beta=1e-12, seed_per=0.0)
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    # E 거의 변동 없음 (foi ≈ 0)
    assert r.states[-1, IDX_E].sum() < 1e-3


# ---------- methods ----------

def test_get_compartment_shape() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    assert r.get_compartment(IDX_S).shape == (len(r.t), N_AGE, N_ADM)


def test_total_by_compartment_shape() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    assert r.total_by_compartment().shape == (len(r.t), 5)


def test_total_by_age_shape() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    assert r.total_by_age().shape == (len(r.t), 5, N_AGE)


def test_attack_rate_excludes_V() -> None:
    """attack_rate = (I+R)/N, V는 제외."""
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 20))
    ar = r.attack_rate(s["pop"])
    # 시간 진행에 따라 단조 증가 (전체 합산)
    ar_total = ((r.states[:, IDX_I] + r.states[:, IDX_R]).sum(axis=(1, 2))) / s["pop"].sum()
    assert (np.diff(ar_total) >= -1e-9).all()
    assert ar.shape == (len(r.t), N_AGE, N_ADM)


def test_daily_new_infection_shape() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    inc = r.daily_new_infection()
    assert inc.shape == (len(r.t) - 1,)
    # 신규 감염 누적 ≥ 0
    assert (inc >= -1e-3).all()


def test_vaccinated_count_shape() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 10))
    assert r.vaccinated_count().shape == (len(r.t), N_AGE, N_ADM)


def test_vaccinated_total_increases() -> None:
    s = _setup()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 30))
    V_t = r.vaccinated_total()
    assert V_t.shape == (len(r.t),)
    assert V_t[-1] > V_t[0]


# ---------- performance ----------

def test_simulation_speed() -> None:
    s = _setup()
    t0 = time.perf_counter()
    r = run_simulation(s["state"], s["mobility"], s["matrices"], s["pop"], s["params"], t_span=(0, 30))
    assert r.success
    assert time.perf_counter() - t0 < 10.0
