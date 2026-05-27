import math
import pandas as pd
import pytest

from backend.insights.diagnostics import decompose_units_growth


def test_decompose_units_growth_distribution_driven_with_interaction_folded_in():
    result = decompose_units_growth(
        units_current=840,
        units_prior=500,
        active_pods_current=140,
        active_pods_prior=100,
        vpo_current=1.5,
        vpo_prior=1.25,
        weeks_per_month=4,
    )

    assert result["total_change"] == 340
    assert result["distribution_impact"] == 240
    assert result["velocity_impact"] == 100
    assert math.isclose(result["distribution_share"], 240 / 340)
    assert math.isclose(result["velocity_share"], 100 / 340)
    assert result["primary_driver"] == "distribution"


def test_decompose_units_growth_velocity_driven():
    result = decompose_units_growth(
        units_current=700,
        units_prior=500,
        active_pods_current=100,
        active_pods_prior=100,
        vpo_current=1.75,
        vpo_prior=1.25,
        weeks_per_month=4,
    )

    assert result["total_change"] == 200
    assert result["distribution_impact"] == 0
    assert result["velocity_impact"] == 200
    assert result["distribution_share"] == 0
    assert result["velocity_share"] == 1
    assert result["primary_driver"] == "velocity"


def test_decompose_units_growth_decline_from_distribution():
    result = decompose_units_growth(
        units_current=400,
        units_prior=500,
        active_pods_current=80,
        active_pods_prior=100,
        vpo_current=1.25,
        vpo_prior=1.25,
        weeks_per_month=4,
    )

    assert result["total_change"] == -100
    assert result["distribution_impact"] == -100
    assert result["velocity_impact"] == 0
    assert result["distribution_share"] == 1
    assert result["velocity_share"] == 0
    assert result["primary_driver"] == "distribution"


def test_decompose_units_growth_returns_none_when_no_change():
    result = decompose_units_growth(
        units_current=500,
        units_prior=500,
        active_pods_current=100,
        active_pods_prior=100,
        vpo_current=1.25,
        vpo_prior=1.25,
    )

    assert result is None


@pytest.mark.parametrize(
    "bad_value",
    [None, float("nan"), pd.NA],
)
def test_decompose_units_growth_returns_none_when_inputs_missing(bad_value):
    result = decompose_units_growth(
        units_current=bad_value,
        units_prior=500,
        active_pods_current=100,
        active_pods_prior=100,
        vpo_current=1.25,
        vpo_prior=1.25,
    )

    assert result is None


def test_decomposition_impacts_reconcile_to_total_change():
    result = decompose_units_growth(
        units_current=960,
        units_prior=500,
        active_pods_current=160,
        active_pods_prior=100,
        vpo_current=1.5,
        vpo_prior=1.25,
        weeks_per_month=4,
    )

    assert math.isclose(
        result["distribution_impact"] + result["velocity_impact"],
        result["total_change"],
    )

def test_decompose_units_growth_mixed_decline_velocity_driver():
    result = decompose_units_growth(
        units_current=360,
        units_prior=500,
        active_pods_current=110,
        active_pods_prior=100,
        vpo_current=0.8181818182,
        vpo_prior=1.25,
        weeks_per_month=4,
    )

    assert result["total_change"] == -140
    assert math.isclose(result["distribution_impact"], 32.727272728)
    assert math.isclose(result["velocity_impact"], -172.72727272)
    assert math.isclose(
        result["distribution_impact"] + result["velocity_impact"],
        result["total_change"],
    )
    assert result["primary_driver"] == "velocity"


def test_decompose_units_growth_distribution_down_but_velocity_up():
    result = decompose_units_growth(
        units_current=480,
        units_prior=500,
        active_pods_current=80,
        active_pods_prior=100,
        vpo_current=1.5,
        vpo_prior=1.25,
        weeks_per_month=4,
    )

    assert result["total_change"] == -20
    assert result["distribution_impact"] == -120
    assert result["velocity_impact"] == 100
    assert result["primary_driver"] == "distribution"


def test_decompose_units_growth_distribution_up_but_velocity_down():
    result = decompose_units_growth(
        units_current=480,
        units_prior=500,
        active_pods_current=120,
        active_pods_prior=100,
        vpo_current=1.0,
        vpo_prior=1.25,
        weeks_per_month=4,
    )

    assert result["total_change"] == -20
    assert result["distribution_impact"] == 80
    assert result["velocity_impact"] == -100
    assert result["primary_driver"] == "velocity"


def test_decompose_units_growth_zero_prior_pods_still_distribution_driven():
    result = decompose_units_growth(
        units_current=400,
        units_prior=0,
        active_pods_current=100,
        active_pods_prior=0,
        vpo_current=1.0,
        vpo_prior=0,
        weeks_per_month=4,
    )

    assert result["total_change"] == 400
    assert result["distribution_impact"] == 400
    assert result["velocity_impact"] == 0
    assert result["distribution_share"] == 1
    assert result["velocity_share"] == 0
    assert result["primary_driver"] == "distribution"


def test_decompose_units_growth_zero_current_pods_full_distribution_loss():
    result = decompose_units_growth(
        units_current=0,
        units_prior=500,
        active_pods_current=0,
        active_pods_prior=100,
        vpo_current=0,
        vpo_prior=1.25,
        weeks_per_month=4,
    )

    assert result["total_change"] == -500
    assert result["distribution_impact"] == 0
    assert result["velocity_impact"] == -500
    assert result["primary_driver"] == "velocity"