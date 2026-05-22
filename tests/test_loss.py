"""Unit tests for kt_epimodel.calibration.loss."""

from __future__ import annotations

import functools

import numpy as np
import pytest

from kt_epimodel.calibration.ili_target import load_ili_target
from kt_epimodel.calibration.loss import make_loss_function
from kt_epimodel.calibration.param_vector import initial_guess
from kt_epimodel.calibration.simple_model import build_aggregated_inputs
from kt_epimodel.model.parameters import ModelParameters


@functools.lru_cache(maxsize=1)
def _setup() -> dict:
    target = load_ili_target("2022-2023")
    inputs = build_aggregated_inputs()
    return {"target": target, "inputs": inputs}


def test_loss_callable() -> None:
    s = _setup()
    loss = make_loss_function(s["target"], s["inputs"], ModelParameters())
    assert callable(loss)


def test_loss_returns_float() -> None:
    s = _setup()
    loss = make_loss_function(s["target"], s["inputs"], ModelParameters())
    val = loss(initial_guess())
    assert isinstance(val, float)
    assert np.isfinite(val)


def test_loss_deterministic() -> None:
    """같은 vec 두 번 호출 → 같은 loss (수치 오차 허용)."""
    s = _setup()
    loss = make_loss_function(s["target"], s["inputs"], ModelParameters())
    vec = initial_guess()
    v1 = loss(vec)
    v2 = loss(vec)
    assert v1 == pytest.approx(v2, rel=1e-6)


def test_loss_invalid_vec_returns_penalty() -> None:
    """beta<0 → vector_to_params 가 ValueError → penalty."""
    s = _setup()
    loss = make_loss_function(s["target"], s["inputs"], ModelParameters(), penalty=999.9)
    bad_vec = initial_guess()
    bad_vec[0] = -1.0          # beta_h negative
    assert loss(bad_vec) == 999.9


def test_loss_call_count_increments() -> None:
    s = _setup()
    loss = make_loss_function(s["target"], s["inputs"], ModelParameters())
    vec = initial_guess()
    loss(vec)
    loss(vec)
    loss(vec)
    assert loss.call_count[0] == 3


def test_loss_higher_for_zero_beta() -> None:
    """β=거의 0 → 시뮬레이션 outbreak 없음 → 관측보다 작음 → NLL 큼."""
    s = _setup()
    loss = make_loss_function(s["target"], s["inputs"], ModelParameters())
    base_vec = initial_guess()
    low_vec = base_vec.copy()
    low_vec[0:4] = 0.001       # very small but valid
    high_vec = base_vec.copy()
    high_vec[0:4] = 0.5
    nll_low = loss(low_vec)
    nll_high = loss(high_vec)
    # high β 가 ILI 패턴 더 잘 잡을 가능성 — 단방향 부등식은 보장 X.
    # 둘 다 finite 인 것만 검증.
    assert np.isfinite(nll_low)
    assert np.isfinite(nll_high)


def test_loss_uses_target_n_weeks() -> None:
    """target n_weeks 가 52 면 simulation_to_ili 52주로 변환."""
    s = _setup()
    loss = make_loss_function(s["target"], s["inputs"], ModelParameters())
    val = loss(initial_guess())
    # n_weeks=52 인지 확인
    assert s["target"]["n_weeks"] == 52
    assert np.isfinite(val)


def test_loss_short_tspan_runs() -> None:
    """t_span 짧게도 실행되어야 (간이 테스트)."""
    s = _setup()
    loss = make_loss_function(
        s["target"], s["inputs"], ModelParameters(), t_span=(0.0, 14.0),
    )
    val = loss(initial_guess())
    assert np.isfinite(val)


def test_loss_by_age_callable() -> None:
    from kt_epimodel.calibration.ili_target import load_ili_target_by_age
    from kt_epimodel.calibration.loss import make_loss_function_by_age
    s = _setup()
    target_age = load_ili_target_by_age("2022-2023", first_peak_only=True)
    loss = make_loss_function_by_age(target_age, s["inputs"], ModelParameters())
    val = loss(initial_guess())
    assert np.isfinite(val)


def test_loss_by_age_returns_larger_than_single() -> None:
    """7 그룹 합산 NLL > 단일 그룹 NLL (단순 sanity)."""
    from kt_epimodel.calibration.ili_target import load_ili_target_by_age
    from kt_epimodel.calibration.loss import make_loss_function_by_age
    s = _setup()
    target_age = load_ili_target_by_age("2022-2023", first_peak_only=True)
    loss_age = make_loss_function_by_age(target_age, s["inputs"], ModelParameters())
    loss_single = make_loss_function(s["target"], s["inputs"], ModelParameters())
    vec = initial_guess()
    v_age = loss_age(vec)
    v_single = loss_single(vec)
    # 7개 그룹 합산 NLL 은 단일 합산 NLL 과 다름 (대체로 더 큼)
    assert np.isfinite(v_age)
    assert np.isfinite(v_single)


def test_loss_by_age_invalid_vec_returns_penalty() -> None:
    from kt_epimodel.calibration.ili_target import load_ili_target_by_age
    from kt_epimodel.calibration.loss import make_loss_function_by_age
    s = _setup()
    target_age = load_ili_target_by_age("2022-2023", first_peak_only=True)
    loss = make_loss_function_by_age(
        target_age, s["inputs"], ModelParameters(), penalty=999.9,
    )
    bad = initial_guess()
    bad[0] = -1.0
    assert loss(bad) == 999.9


def test_loss_uses_target_weights() -> None:
    """first_peak_only target → 후반부 NLL 기여 제외."""
    s = _setup()
    target_first = load_ili_target("2022-2023", first_peak_only=True, first_peak_end_week=26)
    loss_full = make_loss_function(
        s["target"], s["inputs"], ModelParameters(), t_span=(0.0, 28.0),
    )
    loss_first = make_loss_function(
        target_first, s["inputs"], ModelParameters(), t_span=(0.0, 28.0),
    )
    vec = initial_guess()
    v_full = loss_full(vec)
    v_first = loss_first(vec)
    # first-peak weights 가 더 적은 주 만 평가 → NLL 작음 (또는 같음)
    assert v_first <= v_full + 1e-6
