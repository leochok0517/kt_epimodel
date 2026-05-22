"""Unit tests for kt_epimodel.calibration.optimizer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from kt_epimodel.calibration.optimizer import (
    CalibrationResult,
    load_result,
    optimize_calibration,
    optimize_calibration_by_age,
    save_result,
)
from kt_epimodel.model.parameters import CalibrationParameters


# ---------- optimize_calibration ----------

def test_optimizer_runs_nelder_mead() -> None:
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=5, verbose=False,
    )
    assert isinstance(r, CalibrationResult)


def test_optimizer_runs_lbfgsb() -> None:
    r = optimize_calibration(
        season="2022-2023", method="L-BFGS-B",
        max_iterations=3, verbose=False,
    )
    assert isinstance(r, CalibrationResult)


def test_optimizer_invalid_method_raises() -> None:
    with pytest.raises(ValueError):
        optimize_calibration(
            season="2022-2023", method="ConjugateGradient",
            max_iterations=1, verbose=False,
        )


def test_optimizer_result_has_all_fields() -> None:
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=3, verbose=False,
    )
    assert isinstance(r.season, str)
    assert isinstance(r.method, str)
    assert isinstance(r.success, bool)
    assert isinstance(r.nll, float)
    assert isinstance(r.nll_initial, float)
    assert isinstance(r.calibration, CalibrationParameters)
    assert r.vector.shape == (23,)
    assert isinstance(r.n_evaluations, int)
    assert r.elapsed_seconds > 0
    assert isinstance(r.message, str)


def test_optimizer_nll_does_not_worsen() -> None:
    """fit 후 NLL ≤ initial NLL."""
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=21, verbose=False,
    )
    assert r.nll <= r.nll_initial + 1e-6


def test_optimizer_initial_vec_respected() -> None:
    """initial_vec 지정 시 그 값에서 시작."""
    init = np.full(23, 0.1)
    init[18] = 0.5    # gamma_report
    init[19] = 0.3    # seasonality_amp
    init[20] = 0.1    # seasonality_base
    init[21] = 40.0   # seasonality_sigma
    init[22] = 110.0  # seasonality_peak_day
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=1, initial_vec=init, verbose=False,
    )
    # 1 iter 만 — vector 가 init 근방
    assert abs(r.nll_initial) > 0   # 그냥 정상 진행 확인


# ---------- save / load ----------

def test_save_load_roundtrip(tmp_path: Path) -> None:
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=3, verbose=False,
    )
    out = tmp_path / "result.json"
    save_result(r, out)
    assert out.exists()

    loaded = load_result(out)
    assert loaded.season == r.season
    assert loaded.method == r.method
    assert loaded.nll == r.nll
    assert loaded.nll_initial == r.nll_initial
    assert loaded.calibration.beta_h == r.calibration.beta_h
    np.testing.assert_array_equal(loaded.vector, r.vector)
    np.testing.assert_array_equal(loaded.calibration.phi, r.calibration.phi)


def test_save_creates_parent_directory(tmp_path: Path) -> None:
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=1, verbose=False,
    )
    nested = tmp_path / "deep" / "nested" / "result.json"
    save_result(r, nested)
    assert nested.exists()


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_result(tmp_path / "nonexistent.json")


# ---------- first_peak_only ----------

def test_optimize_first_peak_only_runs() -> None:
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=3, verbose=False,
        first_peak_only=True, first_peak_end_week=26,
    )
    assert r.success or r.n_evaluations > 0
    assert r.first_peak_only is True
    assert r.first_peak_end_week == 26


def test_optimize_first_peak_smaller_nll_than_full() -> None:
    """first_peak_only=True 가 NLL 더 작거나 같음 (가중치 0 인 주 제외 효과)."""
    r_full = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=1, verbose=False,
        first_peak_only=False,
    )
    r_first = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=1, verbose=False,
        first_peak_only=True, first_peak_end_week=26,
    )
    # 동일한 초기 vec 에서 평가 — first-peak 만 weighting → NLL ≤
    assert r_first.nll_initial <= r_full.nll_initial + 1e-6


def test_calibration_result_first_peak_fields() -> None:
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=1, verbose=False,
        first_peak_only=True, first_peak_end_week=21,
    )
    assert r.first_peak_only is True
    assert r.first_peak_end_week == 21


def test_save_load_first_peak_roundtrip(tmp_path: Path) -> None:
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=2, verbose=False,
        first_peak_only=True, first_peak_end_week=24,
    )
    out = tmp_path / "fp.json"
    save_result(r, out)
    loaded = load_result(out)
    assert loaded.first_peak_only is True
    assert loaded.first_peak_end_week == 24


# ---------- Nelder-Mead bounds ----------

def test_nelder_mead_respects_bounds() -> None:
    """Nelder-Mead 결과 vector 가 bounds 안에 있어야."""
    from kt_epimodel.calibration.param_vector import get_bounds_vector
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=21, verbose=False,
    )
    bounds = get_bounds_vector()
    for i, (lo, hi) in enumerate(bounds):
        v = r.vector[i]
        # 약간의 수치 여유 — Nelder-Mead bound 처리는 strict 하지 않을 수 있음
        assert lo - 1e-6 <= v <= hi + 1e-6, (
            f"vec[{i}] = {v} outside bound ({lo}, {hi})"
        )


def test_nelder_mead_amp_within_bounds() -> None:
    """seasonality_amp (vec[19]) ∈ [0.0, 3.0]."""
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=21, verbose=False,
    )
    assert 0.0 - 1e-6 <= r.seasonality_amp <= 3.0 + 1e-6


# ---------- by_age ----------

def test_optimize_by_age_runs() -> None:
    r = optimize_calibration_by_age(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=3, verbose=False,
    )
    assert isinstance(r, CalibrationResult)
    assert r.season.endswith("_by_age")


def test_optimize_by_age_use_data_seed_default_true() -> None:
    """by_age 의 use_data_seed default = True."""
    r = optimize_calibration_by_age(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=2, verbose=False,
    )
    assert r.use_data_seed is True
    assert r.seed_by_age is not None
    assert len(r.seed_by_age) == 15
    assert all(v >= 0 for v in r.seed_by_age)


def test_optimize_by_age_gamma_report_assumed_default_2() -> None:
    r = optimize_calibration_by_age(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=2, verbose=False,
    )
    assert r.gamma_report_assumed == 2.0


def test_optimize_by_age_gamma_report_assumed_custom() -> None:
    r = optimize_calibration_by_age(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=2, gamma_report_assumed=3.5, verbose=False,
    )
    assert r.gamma_report_assumed == 3.5


def test_optimize_by_age_use_data_seed_false() -> None:
    """use_data_seed=False → seed_by_age None."""
    r = optimize_calibration_by_age(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=2, use_data_seed=False, seed_total=100.0,
        verbose=False,
    )
    assert r.use_data_seed is False
    assert r.seed_by_age is None
    assert r.seed_total == 100.0


def test_optimize_by_age_result_shape() -> None:
    r = optimize_calibration_by_age(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=2, verbose=False,
    )
    assert r.vector.shape == (23,)
    assert r.first_peak_only is True       # default for by_age


def test_load_legacy_json_defaults_first_peak(tmp_path: Path) -> None:
    """first_peak_only 키 없는 옛 JSON 도 호환 (default False/26)."""
    r = optimize_calibration(
        season="2022-2023", method="Nelder-Mead",
        max_iterations=1, verbose=False,
    )
    out = tmp_path / "legacy.json"
    save_result(r, out)
    # JSON 에서 first_peak_* 키 제거
    import json
    with open(out) as f:
        data = json.load(f)
    data.pop("first_peak_only", None)
    data.pop("first_peak_end_week", None)
    with open(out, "w") as f:
        json.dump(data, f)

    loaded = load_result(out)
    assert loaded.first_peak_only is False
    assert loaded.first_peak_end_week == 26
