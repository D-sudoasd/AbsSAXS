"""Tests for absolute-scale fluorescence subtraction."""

import numpy as np
import pytest

from saxsabs.core.fluorescence_subtraction import (
    FluorescenceSubtractionResult,
    combine_sequential_standard_uncertainties,
    parse_fluorescence_method,
    subtract_fluorescence,
)

ABS = {
    "intensity_state": "absolute_cm^-1",
    "intensity_unit": "1/cm",
    "i_col": "I_abs_cm^-1",
    "operator_provenance": {
        "intensity_state": "absolute_cm^-1",
        "corrections_applied": '["k","thickness"]',
    },
}


def _sub(*args, **kwargs):
    kwargs.setdefault("sample_profile", ABS)
    return subtract_fluorescence(*args, **kwargs)


def test_parse_fluorescence_method_aliases():
    assert parse_fluorescence_method("measured").value == "measured_profile"
    assert parse_fluorescence_method("HIGH_Q_MEAN").value == "high_q_mean"
    with pytest.raises(ValueError, match="fluorescence method"):
        parse_fluorescence_method("compton")


def test_constant_subtraction_and_error():
    q = np.array([0.01, 0.02, 0.20])
    i = np.array([12.0, 11.0, 6.0])
    e = np.array([0.1, 0.1, 0.2])
    out = _sub(
        q,
        i,
        e,
        method="constant",
        f0=2.0,
        f0_uncertainty=0.0,
        beta=1.0,
        beta_uncertainty=0.0,
    )
    assert isinstance(out, FluorescenceSubtractionResult)
    np.testing.assert_allclose(out.i_subtracted, [10.0, 9.0, 4.0])
    np.testing.assert_allclose(out.err_subtracted, e)
    np.testing.assert_allclose(out.err_statistical, e)
    assert out.negative_fraction == 0.0
    assert out.method == "constant"
    assert out.f0 == pytest.approx(2.0)


def test_fluorescence_residual_diagnostic_is_tri_state_for_too_few_points():
    out = _sub(
        np.array([0.01, 0.02, 0.20]),
        np.array([12.0, 11.0, 6.0]),
        np.full(3, 0.1),
        method="constant",
        f0=2.0,
        f0_uncertainty=0.0,
        beta=1.0,
        beta_uncertainty=0.0,
    )

    assert out.high_q_residual_mean is None
    assert out.high_q_check_passed is None


def test_beta_scales_constant_and_propagates_beta_uncertainty():
    q = np.array([0.01, 0.02, 0.03])
    out = _sub(
        q,
        np.full(3, 10.0),
        np.full(3, 0.1),
        method="constant",
        f0=2.0,
        f0_uncertainty=0.0,
        beta=1.5,
        beta_uncertainty=0.05,
    )
    np.testing.assert_allclose(out.i_subtracted, 7.0)
    expected = np.sqrt(0.1**2 + (2.0 * 0.05) ** 2)
    np.testing.assert_allclose(out.err_subtracted, expected)
    np.testing.assert_allclose(out.err_statistical, 0.1)
    np.testing.assert_allclose(out.f_profile, 2.0)


def test_missing_f0_uncertainty_keeps_combined_unknown():
    q = np.array([0.01, 0.02, 0.20])
    out = _sub(
        q,
        np.ones(3) * 5.0,
        np.ones(3) * 0.1,
        method="constant",
        f0=1.0,
    )
    assert out.f0_uncertainty is None
    np.testing.assert_allclose(out.err_statistical, 0.1)
    assert np.all(np.isnan(out.err_subtracted))


def test_f0_uncertainty_enters_statistical_and_combined():
    q = np.array([0.01, 0.02, 0.03])
    out = _sub(
        q,
        np.full(3, 8.0),
        np.full(3, 0.2),
        method="constant",
        f0=1.0,
        f0_uncertainty=0.3,
        beta=2.0,
        beta_uncertainty=0.0,
    )
    expected = np.sqrt(0.2**2 + (2.0 * 0.3) ** 2)
    np.testing.assert_allclose(out.err_statistical, expected)
    np.testing.assert_allclose(out.err_subtracted, expected)


def test_high_q_mean_estimates_planted_constant():
    q = np.linspace(0.01, 0.30, 60)
    i = np.exp(-q / 0.02) + 3.5
    out = _sub(
        q,
        i,
        np.full_like(q, 0.01),
        method="high_q_mean",
        high_q_window=(0.25, 0.30),
        f0_uncertainty=0.0,
        beta_uncertainty=0.0,
    )
    assert out.f0 == pytest.approx(3.5, rel=0.02)
    np.testing.assert_allclose(out.i_subtracted, i - out.f0, rtol=1e-12)
    assert out.high_q_points >= 3
    assert out.method == "high_q_mean"


def test_high_q_median_is_robust_to_one_spike():
    q = np.linspace(0.20, 0.30, 11)
    i = np.full(q.shape, 4.0)
    i[5] = 40.0
    mean_out = _sub(
        q, i, np.full_like(q, 0.01), method="high_q_mean",
        high_q_window=(0.20, 0.30), f0_uncertainty=0.0, beta_uncertainty=0.0,
    )
    median_out = _sub(
        q, i, np.full_like(q, 0.01), method="high_q_median",
        high_q_window=(0.20, 0.30), f0_uncertainty=0.0, beta_uncertainty=0.0,
    )
    assert mean_out.f0 > median_out.f0
    assert median_out.f0 == pytest.approx(4.0)


def test_measured_profile_interpolates_like_buffer():
    q_s = np.array([1.0])
    q_f = np.array([0.0, 2.0])
    out = _sub(
        q_s,
        np.array([10.0]),
        np.array([0.4]),
        method="measured_profile",
        q_fluorescence=q_f,
        i_fluorescence=np.array([2.0, 4.0]),
        err_fluorescence=np.array([1.0, 3.0]),
        fluorescence_profile=ABS,
        beta=1.0,
        beta_uncertainty=0.0,
    )
    assert out.i_subtracted[0] == pytest.approx(7.0)
    assert out.err_subtracted[0] == pytest.approx(np.sqrt(0.4**2 + 2.5))
    assert out.f0 == pytest.approx(3.0)


def test_measured_missing_curve_uncertainty_keeps_results_unknown():
    q = np.array([0.01, 0.02, 0.03])
    out = _sub(
        q,
        np.full(3, 10.0),
        np.full(3, 0.1),
        method="measured",
        q_fluorescence=q,
        i_fluorescence=np.full(3, 2.0),
        err_fluorescence=None,
        fluorescence_profile=ABS,
        beta_uncertainty=0.0,
    )
    assert np.all(np.isnan(out.err_statistical))
    assert np.all(np.isnan(out.err_subtracted))


def test_refuses_unlabeled_and_negative_f0():
    q = np.array([0.01, 0.02, 0.03])
    with pytest.raises(ValueError, match="sample_profile"):
        subtract_fluorescence(q, np.ones(3), np.ones(3), method="constant", f0=1.0)
    with pytest.raises(ValueError, match="f0"):
        _sub(q, np.ones(3) * 5, np.ones(3) * 0.1, method="constant", f0=-0.1)


def test_subtract_fluorescence_rejects_empty_public_arrays():
    with pytest.raises(ValueError, match="empty"):
        _sub(
            np.array([]),
            np.array([]),
            np.array([]),
            method="constant",
            f0=1.0,
        )


def test_already_fluorescence_subtracted_is_refused():
    q = np.array([0.01, 0.02, 0.03])
    profile = {
        **ABS,
        "operator_provenance": {
            "intensity_state": "absolute_cm^-1",
            "corrections_applied": '["fluorescence","k","thickness"]',
        },
    }
    with pytest.raises(ValueError, match="already fluorescence-subtracted"):
        subtract_fluorescence(
            q, np.ones(3) * 5, np.ones(3) * 0.1,
            sample_profile=profile, method="constant", f0=1.0,
        )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"method": "nope", "f0": 1.0}, "fluorescence method"),
        ({"method": "high_q_mean"}, "high_q_window"),
        (
            {
                "method": "high_q_mean",
                "high_q_window": (0.29, 0.30),
            },
            "at least 3",
        ),
        ({"method": "measured_profile"}, "fluorescence_profile"),
        ({"method": "constant", "f0": 1.0, "beta": 0.0}, "beta"),
        ({"method": "constant"}, "requires f0"),
        (
            {"method": "high_q_mean", "high_q_window": (0.01, 0.03), "f0": 1.0},
            "refuse a user f0",
        ),
    ],
)
def test_invalid_method_arguments_raise(kwargs, match):
    q = np.array([0.01, 0.02, 0.03])
    with pytest.raises(ValueError, match=match):
        _sub(q, np.full(3, 5.0), np.full(3, 0.1), **kwargs)


def test_measured_profile_outside_q_range_raises():
    q_s = np.array([0.01, 0.20, 0.40])
    q_f = np.array([0.05, 0.10, 0.30])
    with pytest.raises(ValueError, match="outside fluorescence q range"):
        _sub(
            q_s,
            np.ones(3) * 10.0,
            np.ones(3) * 0.1,
            method="measured",
            q_fluorescence=q_f,
            i_fluorescence=np.ones(3) * 2.0,
            err_fluorescence=np.ones(3) * 0.05,
            fluorescence_profile=ABS,
            beta_uncertainty=0.0,
        )


def test_negative_err_abs_raises():
    q = np.array([0.01, 0.02, 0.03])
    with pytest.raises(ValueError, match="err_abs"):
        _sub(
            q,
            np.ones(3) * 5.0,
            np.array([0.1, -0.2, 0.1]),
            method="constant",
            f0=1.0,
        )


def test_infinite_err_abs_raises():
    q = np.array([0.01, 0.02, 0.03])
    err = np.array([0.1, np.inf, 0.1])
    with pytest.raises(ValueError, match="err_abs"):
        _sub(q, np.ones(3) * 5.0, err, method="constant", f0=1.0)


def test_negative_fraction_is_reported_without_clipping():
    q = np.array([0.01, 0.02, 0.03])
    out = _sub(
        q,
        np.array([1.0, 0.4, 0.1]),
        np.full(3, 0.01),
        method="constant",
        f0=0.5,
        f0_uncertainty=0.0,
        beta_uncertainty=0.0,
    )
    np.testing.assert_allclose(out.i_subtracted, [0.5, -0.1, -0.4])
    assert out.negative_fraction == pytest.approx(2.0 / 3.0)


def test_buffer_then_fluorescence_ledger_is_allowed():
    profile = {
        **ABS,
        "operator_provenance": {
            "intensity_state": "absolute_cm^-1",
            "corrections_applied": '["buffer","k","thickness"]',
        },
    }
    q = np.array([0.01, 0.02, 0.03])
    out = subtract_fluorescence(
        q,
        np.full(3, 4.0),
        np.full(3, 0.1),
        sample_profile=profile,
        method="constant",
        f0=1.0,
        f0_uncertainty=0.0,
        beta_uncertainty=0.0,
    )
    np.testing.assert_allclose(out.i_subtracted, 3.0)


def test_shipped_buffer_then_fluorescence_keeps_statistical_and_unknown_extras():
    """Drive the real Tab3 composition: buffer kernel then fluorescence kernel."""
    from saxsabs.core.buffer_subtraction import subtract_buffer

    q = np.array([0.01, 0.02, 0.03])
    i_sample = np.array([12.0, 11.0, 10.0])
    i_buffer = np.full(3, 2.0)
    err_sample = np.full(3, 0.1)
    err_buffer = np.full(3, 0.2)
    alpha = 0.5
    u_alpha = 0.05
    f0 = 1.0
    u_f0 = 0.3
    beta = 1.0
    u_beta = 0.04

    buffered = subtract_buffer(
        q,
        i_sample,
        err_sample,
        q,
        i_buffer,
        err_buffer,
        alpha=alpha,
        alpha_uncertainty=u_alpha,
        sample_profile=ABS,
        buffer_profile=ABS,
    )
    after_buffer = {
        **ABS,
        "operator_provenance": {
            "intensity_state": "absolute_cm^-1",
            "corrections_applied": '["buffer","k","thickness"]',
        },
    }
    fluo = subtract_fluorescence(
        buffered.q,
        buffered.i_subtracted,
        buffered.err_statistical,
        sample_profile=after_buffer,
        method="constant",
        f0=f0,
        f0_uncertainty=u_f0,
        beta=beta,
        beta_uncertainty=u_beta,
    )
    stat, comb = combine_sequential_standard_uncertainties(
        buffered.err_statistical,
        buffered.err_subtracted,
        fluo.err_statistical,
        fluo.err_subtracted,
    )

    np.testing.assert_allclose(fluo.i_subtracted, i_sample - alpha * i_buffer - f0)
    expected_stat = np.sqrt(err_sample**2 + (alpha * err_buffer) ** 2 + (beta * u_f0) ** 2)
    np.testing.assert_allclose(stat, expected_stat)
    expected_comb = np.sqrt(
        expected_stat**2 + (i_buffer * u_alpha) ** 2 + (f0 * u_beta) ** 2
    )
    np.testing.assert_allclose(comb, expected_comb)

    unknown_alpha = subtract_buffer(
        q,
        i_sample,
        err_sample,
        q,
        i_buffer,
        err_buffer,
        alpha=alpha,
        sample_profile=ABS,
        buffer_profile=ABS,
    )
    fluo_after_unknown = subtract_fluorescence(
        unknown_alpha.q,
        unknown_alpha.i_subtracted,
        unknown_alpha.err_statistical,
        sample_profile=after_buffer,
        method="constant",
        f0=f0,
        f0_uncertainty=u_f0,
        beta=beta,
        beta_uncertainty=u_beta,
    )
    _stat2, comb2 = combine_sequential_standard_uncertainties(
        unknown_alpha.err_statistical,
        unknown_alpha.err_subtracted,
        fluo_after_unknown.err_statistical,
        fluo_after_unknown.err_subtracted,
    )
    np.testing.assert_allclose(_stat2, expected_stat)
    assert np.all(np.isnan(comb2))


def test_combine_sequential_keeps_unknown_previous_combined():
    stat, comb = combine_sequential_standard_uncertainties(
        np.array([0.2, 0.2]),
        np.array([np.nan, np.nan]),
        np.array([0.3, 0.3]),
        np.array([0.4, 0.4]),
    )
    np.testing.assert_allclose(stat, 0.3)
    assert np.all(np.isnan(comb))


def test_combine_sequential_adds_independent_extras():
    prev_stat = np.array([0.1])
    prev_comb = np.array([np.sqrt(0.1**2 + 0.3**2)])
    next_stat = np.array([np.sqrt(0.1**2 + 0.2**2)])
    next_comb = np.array([np.sqrt(0.1**2 + 0.2**2 + 0.4**2)])
    stat, comb = combine_sequential_standard_uncertainties(
        prev_stat, prev_comb, next_stat, next_comb
    )
    np.testing.assert_allclose(stat, next_stat)
    np.testing.assert_allclose(comb, np.sqrt(0.1**2 + 0.2**2 + 0.3**2 + 0.4**2))


def test_combine_sequential_rejects_broadcastable_but_unequal_shapes():
    with pytest.raises(ValueError, match="exactly equal shapes"):
        combine_sequential_standard_uncertainties(
            np.ones(2),
            np.ones(2),
            np.ones(1),
            np.ones(1),
        )


def test_combine_sequential_validates_previous_statistical_shape_without_combined():
    with pytest.raises(ValueError, match="exactly equal shapes"):
        combine_sequential_standard_uncertainties(
            np.ones(2),
            None,
            np.ones(1),
            np.ones(1),
        )


def test_combine_sequential_rejects_finite_overflow_without_warning():
    with pytest.raises(ValueError, match="overflowed"):
        combine_sequential_standard_uncertainties(
            np.full(2, 1.0e200),
            np.full(2, 2.0e200),
            np.full(2, 1.0e200),
            np.full(2, 2.0e200),
        )


def test_combine_sequential_rejects_infinite_next_combined_before_none_early_return():
    with pytest.raises(ValueError, match="must not contain infinities"):
        combine_sequential_standard_uncertainties(
            np.array([1.0]),
            None,
            np.array([1.0]),
            np.array([np.inf]),
        )


@pytest.mark.parametrize("argument", ["previous_statistical", "next_statistical"])
def test_combine_sequential_rejects_infinite_statistical_inputs(argument):
    kwargs = {
        "previous_statistical": np.array([1.0]),
        "previous_combined": None,
        "next_statistical": np.array([1.0]),
        "next_combined": np.array([1.0]),
    }
    kwargs[argument] = np.array([np.inf])

    with pytest.raises(ValueError, match="must not contain infinities"):
        combine_sequential_standard_uncertainties(**kwargs)


def test_combine_sequential_preserves_nan_unknown_with_none_previous_combined():
    stat, combined = combine_sequential_standard_uncertainties(
        np.array([1.0]),
        None,
        np.array([1.0]),
        np.array([np.nan]),
    )

    np.testing.assert_allclose(stat, [1.0])
    assert np.isnan(combined[0])


def test_fluorescence_rejects_extreme_finite_beta_as_controlled_error():
    with pytest.raises(ValueError, match="overflowed"):
        _sub(
            np.array([0.01, 0.02, 0.03]),
            np.full(3, 10.0),
            np.zeros(3),
            method="constant",
            f0=1.0,
            f0_uncertainty=0.0,
            beta=1.0e200,
            beta_uncertainty=0.0,
        )
