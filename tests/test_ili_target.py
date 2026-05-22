"""Unit tests for kt_epimodel.calibration.ili_target."""

from __future__ import annotations

import numpy as np
import pytest

from kt_epimodel.calibration.ili_target import (
    load_ili_target,
    load_ili_target_by_age,
    poisson_log_likelihood,
    season_start_date,
    simulation_to_ili,
    simulation_to_ili_by_age,
)


# ---------- load_ili_target ----------

def test_load_2018_2019() -> None:
    d = load_ili_target("2018-2019")
    assert d["season"] == "2018-2019"
    assert d["n_weeks"] == 52
    # 일부 NaN 보간 후 valid 가 (거의) 전 주에 True
    assert d["is_valid"].sum() >= 50


def test_load_covid_season_low_rate() -> None:
    """2020-2021 코로나 시즌은 평균 ILI 낮음."""
    d = load_ili_target("2020-2021")
    assert np.nanmean(d["ili_rate"]) < 2.0


def test_load_invalid_season_raises() -> None:
    with pytest.raises(ValueError):
        load_ili_target("1999-2000")


def test_load_interpolate_nan_fills() -> None:
    d = load_ili_target("2018-2019", interpolate_nan=True)
    assert not np.isnan(d["ili_rate"]).any() or d["is_valid"].all()


def test_load_no_interpolate_keeps_nan() -> None:
    d_no = load_ili_target("2018-2019", interpolate_nan=False)
    d_yes = load_ili_target("2018-2019", interpolate_nan=True)
    # 보간 안 한 쪽이 NaN 더 많거나 같음
    assert np.isnan(d_no["ili_rate"]).sum() >= np.isnan(d_yes["ili_rate"]).sum()


# ---------- season_start_date ----------

def test_season_start_2018() -> None:
    """2018-2019 시즌 시작 = 2018 ISO 36주 월요일."""
    d = season_start_date("2018-2019")
    # 2018 ISO 36주는 2018-09-03 (월)
    assert d == 20180903


def test_season_start_2022() -> None:
    d = season_start_date("2022-2023")
    # 2022 ISO 36주 월요일
    import datetime
    expected_dt = datetime.date.fromisocalendar(2022, 36, 1)
    expected = expected_dt.year * 10000 + expected_dt.month * 100 + expected_dt.day
    assert d == expected


# ---------- simulation_to_ili ----------

def test_sim_to_ili_shape() -> None:
    daily = np.full(7 * 52, 100.0)
    ili = simulation_to_ili(daily, population=1_000_000, gamma_report=0.5)
    assert ili.shape == (52,)


def test_sim_to_ili_scaling_gamma_report() -> None:
    daily = np.full(7 * 10, 100.0)
    a = simulation_to_ili(daily, population=1_000_000, gamma_report=0.3)
    b = simulation_to_ili(daily, population=1_000_000, gamma_report=0.6)
    np.testing.assert_allclose(b[:10], 2 * a[:10], rtol=1e-12)


def test_sim_to_ili_multi_dim_aggregation() -> None:
    """다차원 입력 → axis>=1 합산."""
    daily_2d = np.full((7 * 10, 5), 100.0)   # (n_days, n_admdong)
    daily_1d = np.full(7 * 10, 500.0)         # 합산 결과와 동일
    a = simulation_to_ili(daily_2d, population=1_000_000, gamma_report=0.5)
    b = simulation_to_ili(daily_1d, population=1_000_000, gamma_report=0.5)
    np.testing.assert_allclose(a, b, rtol=1e-12)


def test_sim_to_ili_padding_when_short() -> None:
    """짧은 시계열 → 0 패딩."""
    daily = np.full(7 * 5, 100.0)
    ili = simulation_to_ili(daily, population=1_000_000, gamma_report=0.5, n_weeks=52)
    assert ili.shape == (52,)
    assert (ili[5:] == 0).all()


def test_sim_to_ili_truncate_when_long() -> None:
    daily = np.full(7 * 60, 100.0)
    ili = simulation_to_ili(daily, population=1_000_000, gamma_report=0.5, n_weeks=52)
    assert ili.shape == (52,)


# ---------- poisson_log_likelihood ----------

def test_poisson_perfect_smaller_than_constant() -> None:
    target = np.array([1.0, 2.0, 3.0, 5.0, 4.0, 2.0, 1.5])
    nll_perfect = poisson_log_likelihood(target, target.copy())
    nll_const   = poisson_log_likelihood(target, np.full_like(target, target.mean()))
    assert nll_perfect < nll_const


def test_poisson_zero_pred_large_nll() -> None:
    target = np.array([1.0, 2.0, 3.0, 5.0, 4.0])
    nll_perfect = poisson_log_likelihood(target, target.copy())
    nll_zero    = poisson_log_likelihood(target, np.full_like(target, 1e-3))
    assert nll_zero > nll_perfect


def test_poisson_invalid_mask_skipped() -> None:
    target = np.array([1.0, 2.0, 3.0, 5.0])
    pred = np.array([1.0, 2.0, 3.0, 100.0])
    mask = np.array([True, True, True, False])
    nll_all = poisson_log_likelihood(target, pred)
    nll_msk = poisson_log_likelihood(target, pred, is_valid=mask)
    # 큰 차이가 있는 4번째 weekend 제외 → NLL 작음
    assert nll_msk < nll_all


def test_poisson_nan_safe() -> None:
    target = np.array([1.0, np.nan, 3.0, 5.0])
    pred   = np.array([1.0, 2.0, np.nan, 5.0])
    nll = poisson_log_likelihood(target, pred)
    assert np.isfinite(nll)


def test_poisson_min_rate_default_is_0_1() -> None:
    """default min_rate = 0.1 — corner solution 방지."""
    obs = np.array([5.0, 10.0, 20.0])
    pred_zero = np.array([0.0, 0.0, 0.0])
    pred_floor = np.full_like(obs, 0.1)
    # default min_rate=0.1 → pred=0 도 0.1 로 clip → 같은 NLL
    nll_default = poisson_log_likelihood(obs, pred_zero)
    nll_floor = poisson_log_likelihood(obs, pred_floor)
    assert nll_default == pytest.approx(nll_floor)


def test_poisson_min_rate_smaller_floor() -> None:
    """min_rate 명시적으로 작게 하면 pred=0 의 NLL 더 커짐."""
    obs = np.array([5.0, 10.0, 20.0])
    pred_zero = np.array([0.0, 0.0, 0.0])
    nll_floor_01 = poisson_log_likelihood(obs, pred_zero, min_rate=0.1)
    nll_floor_tiny = poisson_log_likelihood(obs, pred_zero, min_rate=1e-6)
    # min_rate=1e-6 → -obs·log(1e-6) = +13.8·obs → 큰 NLL
    assert nll_floor_tiny > nll_floor_01


def test_poisson_min_rate_penalizes_corner_solution() -> None:
    """default min_rate=0.1 에서 zero pred 가 합리 pred 보다 NLL 큼."""
    obs = np.array([5.0, 10.0, 20.0, 50.0, 30.0, 10.0])
    pred_zero = np.full_like(obs, 0.001)        # corner solution
    pred_good = np.array([4.0, 9.0, 22.0, 48.0, 28.0, 11.0])
    nll_zero = poisson_log_likelihood(obs, pred_zero)
    nll_good = poisson_log_likelihood(obs, pred_good)
    assert nll_zero > nll_good


def test_poisson_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        poisson_log_likelihood(np.zeros(5), np.zeros(4))


# ---------- weights ----------

def test_load_default_weights_match_is_valid() -> None:
    d = load_ili_target("2018-2019")
    np.testing.assert_array_equal(d["weights"], d["is_valid"].astype(float))


def test_load_first_peak_only_zeroes_late_weeks() -> None:
    d = load_ili_target("2018-2019", first_peak_only=True, first_peak_end_week=26)
    weeks = d["week_in_season"]
    weights = d["weights"]
    # week >= 26 → 0
    assert (weights[weeks >= 26] == 0).all()
    # week < 26 → valid 면 1
    assert (weights[(weeks < 26) & d["is_valid"]] > 0).all()


def test_load_first_peak_end_week_custom() -> None:
    d20 = load_ili_target("2018-2019", first_peak_only=True, first_peak_end_week=20)
    d30 = load_ili_target("2018-2019", first_peak_only=True, first_peak_end_week=30)
    # 30이 20보다 더 많이 포함
    assert (d30["weights"] > 0).sum() > (d20["weights"] > 0).sum()


def test_poisson_uniform_weights_equals_unweighted() -> None:
    obs = np.array([1.0, 2.0, 3.0, 5.0, 4.0])
    pred = np.array([1.0, 2.0, 3.0, 4.0, 4.0])
    nll1 = poisson_log_likelihood(obs, pred)
    nll2 = poisson_log_likelihood(obs, pred, weights=np.ones_like(obs))
    assert nll1 == pytest.approx(nll2)


def test_poisson_zero_weight_skips() -> None:
    """weight=0 인 부분은 NLL 기여 X."""
    obs = np.array([1.0, 2.0, 3.0, 100.0])
    pred = np.array([1.0, 2.0, 3.0, 1.0])    # 마지막 큰 차이
    w_all = np.ones_like(obs)
    w_skip = np.array([1.0, 1.0, 1.0, 0.0])  # 마지막 무시
    nll_all = poisson_log_likelihood(obs, pred, weights=w_all)
    nll_skip = poisson_log_likelihood(obs, pred, weights=w_skip)
    assert nll_skip < nll_all   # 큰 차이가 무시되어 NLL 작음


def test_poisson_weights_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        poisson_log_likelihood(
            np.zeros(5), np.zeros(5), weights=np.ones(4),
        )


# ---------- by-age target ----------

def test_load_target_by_age_shape() -> None:
    t = load_ili_target_by_age("2018-2019")
    assert len(t["age_groups"]) == 7
    for ag in t["age_groups"]:
        assert t["ili_rates"][ag].shape == (52,)
        assert t["weights"][ag].shape == (52,)
        assert t["is_valid"][ag].shape == (52,)


def test_load_target_by_age_first_peak_only() -> None:
    t = load_ili_target_by_age("2018-2019", first_peak_only=True, first_peak_end_week=26)
    weeks = t["week_in_season"]
    for ag in t["age_groups"]:
        w = t["weights"][ag]
        assert (w[weeks >= 26] == 0).all()


def test_load_target_by_age_invalid_season_raises() -> None:
    with pytest.raises(ValueError):
        load_ili_target_by_age("1999-2000")


# ---------- simulation_to_ili_by_age ----------

def test_sim_to_ili_by_age_returns_7_groups() -> None:
    daily = np.full((7 * 10, 15), 10.0)
    pop = np.full(15, 1_000_000.0)
    out = simulation_to_ili_by_age(daily, pop, gamma_report=0.5)
    assert len(out) == 7
    for ag, ili in out.items():
        assert ili.shape == (52,)


def test_sim_to_ili_by_age_gamma_scales() -> None:
    daily = np.full((7 * 10, 15), 10.0)
    pop = np.full(15, 1_000_000.0)
    a = simulation_to_ili_by_age(daily, pop, gamma_report=0.3)
    b = simulation_to_ili_by_age(daily, pop, gamma_report=0.6)
    for ag in a:
        np.testing.assert_allclose(b[ag][:10], 2 * a[ag][:10], rtol=1e-12)


def test_sim_to_ili_by_age_pop_2d() -> None:
    """pop_15 가 (15, n_admdong) 일 때도 작동 (합산)."""
    daily = np.full((7 * 5, 15), 10.0)
    pop = np.full((15, 1), 1_000_000.0)
    out = simulation_to_ili_by_age(daily, pop, gamma_report=0.5)
    assert len(out) == 7


def test_sim_to_ili_by_age_wrong_shape_raises() -> None:
    with pytest.raises(ValueError):
        simulation_to_ili_by_age(np.zeros((10, 14)), np.zeros(15), gamma_report=0.5)


# ---------- weighted vs unweighted ----------

def test_sim_to_ili_by_age_weighted_default_is_true() -> None:
    """use_weighted=True 가 default → WEIGHTED dict 적용."""
    daily = np.full((7 * 5, 15), 10.0)
    pop = np.full(15, 1_000_000.0)
    out_default = simulation_to_ili_by_age(daily, pop, gamma_report=0.5)
    out_weighted = simulation_to_ili_by_age(daily, pop, gamma_report=0.5, use_weighted=True)
    for ag in out_default:
        np.testing.assert_array_equal(out_default[ag], out_weighted[ag])


def test_sim_to_ili_by_age_weighted_vs_unweighted_differs() -> None:
    """weighted ≠ unweighted (heterogeneous incidence)."""
    # 연령별 다른 incidence (0-4 가 다른 그룹과 크게 다름)
    daily = np.ones((7 * 5, 15)) * 10.0
    daily[:, 0] = 100.0    # NIMS 0-4 만 10배
    pop = np.full(15, 1_000_000.0)
    w = simulation_to_ili_by_age(daily, pop, gamma_report=0.5, use_weighted=True)
    u = simulation_to_ili_by_age(daily, pop, gamma_report=0.5, use_weighted=False)
    # '0' 그룹: weighted 는 NIMS 0 의 0.2 weight 만 적용 → 100·0.2 / 1M·0.2 = 100/1M.
    # unweighted 는 NIMS 0 전체 합 → 100 / 1M.
    # → ratio 는 동일 (자기 그룹만 포함).
    # 하지만 '1-6' 은 차이 있음:
    #   weighted: (100·0.8 + 10·0.4) / (1M·0.8 + 1M·0.4) = 84/1.2M = 70
    #   unweighted: (100 + 10) / (1M + 1M) = 110/2M = 55
    any_diff = any(
        not np.allclose(w[ag], u[ag], rtol=1e-6) for ag in w
    )
    assert any_diff, "weighted and unweighted should differ for heterogeneous incidence"


def test_sim_to_ili_by_age_weighted_pop_conservation() -> None:
    """weighted 그룹별 group_pop 합 = pop_15 total."""
    from kt_data.data.load_ili import ILI_GROUP_TO_NIMS_WEIGHTED
    pop = np.arange(15, dtype=float) * 100 + 100   # heterogeneous
    total = 0.0
    for weights in ILI_GROUP_TO_NIMS_WEIGHTED.values():
        for nims_idx, w in weights.items():
            total += w * pop[nims_idx]
    # 각 NIMS idx weight 합 = 1.0 → group_pop 합 = pop.sum()
    np.testing.assert_allclose(total, pop.sum(), rtol=1e-12)


def test_sim_to_ili_by_age_weighted_proportional_gamma() -> None:
    daily = np.full((7 * 5, 15), 10.0)
    pop = np.full(15, 1_000_000.0)
    a = simulation_to_ili_by_age(daily, pop, gamma_report=0.3, use_weighted=True)
    b = simulation_to_ili_by_age(daily, pop, gamma_report=0.6, use_weighted=True)
    for ag in a:
        np.testing.assert_allclose(b[ag], 2 * a[ag], rtol=1e-12)


def test_sim_to_ili_by_age_weighted_returns_7_groups() -> None:
    daily = np.full((7 * 5, 15), 10.0)
    pop = np.full(15, 1_000_000.0)
    out = simulation_to_ili_by_age(daily, pop, gamma_report=0.5, use_weighted=True)
    assert len(out) == 7
