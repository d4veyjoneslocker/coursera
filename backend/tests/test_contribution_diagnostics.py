"""
Tests for backend.insights.contribution_diagnostics

Covers:
  - atomic attribution by lifecycle status
  - the reconciliation invariant (dist + vel == total) at atom AND aggregate grain
  - status-as-of join (latest status <= current_end), including sparse tables
  - the "moving row must have a status" tripwire
  - the "unmapped status" reconciliation tripwire
  - outer-join survival of new / lost / quiet placements
  - aggregation to arbitrary grain
  - shares (including the offsetting >100% case)
  - primary_driver: distribution / velocity / balanced / none
  - null-dimension retention
  - empty inputs

Run:  pytest test_contribution_diagnostics.py -v

NOTE: A failing test here is a legitimate result. Several tests assert the
*intended* design behavior rather than whatever the code happens to do; those
are flagged with `# INTENT:` so you can tell a genuine bug from a wrong
expectation. Do not "fix" a test just to make it green — decide first whether
the code or the expectation is what's wrong.
"""

import numpy as np
import pandas as pd
import pytest

from backend.insights.contribution_diagnostics import (
    build_units_contribution_table,
    aggregate_units_contributions,
    calculate_units_growth_decomposition_additive,
    validate_contribution_reconciliation,
    ATOM,
    DISTRIBUTION_STATUSES,
    VELOCITY_STATUSES,
)


# ---------------------------------------------------------
# Window constants (Period[M], matching production assumption)
# ---------------------------------------------------------

PRIOR_START = pd.Period("2025-11", freq="M")
PRIOR_END = pd.Period("2026-01", freq="M")
CURR_START = pd.Period("2026-02", freq="M")
CURR_END = pd.Period("2026-04", freq="M")


# ---------------------------------------------------------
# Builders
# ---------------------------------------------------------

def sales_row(pod, cust, sku, month, units, chain="WF", state="CA", revenue=None):
    return {
        "pod_helper": pod,
        "coded_customer": cust,
        "sku": sku,
        "month_year": pd.Period(month, freq="M"),
        "units": units,
        "revenue": revenue if revenue is not None else units * 1.0,
        "chain": chain,
        "state": state,
    }


def make_sales(rows):
    return pd.DataFrame(rows)


def status_row(pod, cust, sku, status, month=CURR_END):
    return {
        "pod_helper": pod,
        "coded_customer": cust,
        "sku": sku,
        "sku_status": status,
        "month_year": pd.Period(month, freq="M") if not isinstance(month, pd.Period) else month,
    }


def make_status(rows):
    return pd.DataFrame(rows)


def build(df, status, **kw):
    return build_units_contribution_table(
        df=df, status_table=status,
        current_start=CURR_START, current_end=CURR_END,
        prior_start=PRIOR_START, prior_end=PRIOR_END,
        **kw,
    )


# =========================================================
# Attribution by status
# =========================================================

class TestAttribution:

    def test_healthy_change_is_velocity(self):
        # existing placement, sold both periods, units changed -> velocity
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-01", 100),   # prior
            sales_row("p1", "c1", "VAN", "2026-03", 130),   # current
        ])
        status = make_status([status_row("p1", "c1", "VAN", "Healthy")])
        out = build(df, status)
        row = out.iloc[0]
        assert row["total_change"] == 30
        assert row["velocity_impact"] == 30
        assert row["distribution_impact"] == 0

    def test_new_placement_is_distribution(self):
        # only current-period sales, status New -> all distribution
        df = make_sales([
            sales_row("p2", "c1", "VAN", "2026-03", 80),
        ])
        status = make_status([status_row("p2", "c1", "VAN", "New")])
        out = build(df, status)
        row = out.iloc[0]
        assert row["total_change"] == 80
        assert row["distribution_impact"] == 80
        assert row["velocity_impact"] == 0

    def test_inactive_loss_is_distribution(self):
        # sold prior, zero current, status Inactive -> negative distribution
        df = make_sales([
            sales_row("p3", "c1", "VAN", "2026-01", 60),
        ])
        status = make_status([status_row("p3", "c1", "VAN", "Inactive")])
        out = build(df, status)
        row = out.iloc[0]
        assert row["total_change"] == -60
        assert row["distribution_impact"] == -60
        assert row["velocity_impact"] == 0

    def test_revived_is_distribution(self):
        df = make_sales([
            sales_row("p4", "c1", "VAN", "2026-03", 45),
        ])
        status = make_status([status_row("p4", "c1", "VAN", "Revived")])
        out = build(df, status)
        assert out.iloc[0]["distribution_impact"] == 45
        assert out.iloc[0]["velocity_impact"] == 0

    def test_struggling_quiet_this_window_is_velocity(self):
        # INTENT: a placement that sold prior but went quiet this window, if
        # its status is Struggling (not Inactive), should be VELOCITY, not a
        # distribution loss. This is the "don't cry delist on a skipped order"
        # decision.
        df = make_sales([
            sales_row("p5", "c1", "VAN", "2026-01", 50),   # prior only
        ])
        status = make_status([status_row("p5", "c1", "VAN", "Struggling")])
        out = build(df, status)
        row = out.iloc[0]
        assert row["total_change"] == -50
        assert row["velocity_impact"] == -50
        assert row["distribution_impact"] == 0


# =========================================================
# Reconciliation invariant
# =========================================================

class TestReconciliation:

    def test_every_row_reconciles(self):
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-01", 100),
            sales_row("p1", "c1", "VAN", "2026-03", 130),
            sales_row("p2", "c1", "PB", "2026-03", 80),
            sales_row("p3", "c1", "VAN", "2026-01", 60),
        ])
        status = make_status([
            status_row("p1", "c1", "VAN", "Healthy"),
            status_row("p2", "c1", "PB", "New"),
            status_row("p3", "c1", "VAN", "Inactive"),
        ])
        out = build(df, status)
        gap = (out["distribution_impact"] + out["velocity_impact"] - out["total_change"]).abs()
        assert (gap < 1e-6).all()

    def test_aggregate_reconciles_at_every_grain(self):
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-01", 100, chain="WF"),
            sales_row("p1", "c1", "VAN", "2026-03", 130, chain="WF"),
            sales_row("p2", "c2", "PB", "2026-03", 80, chain="SPROUTS"),
            sales_row("p3", "c3", "VAN", "2026-01", 60, chain="SPROUTS"),
        ])
        status = make_status([
            status_row("p1", "c1", "VAN", "Healthy"),
            status_row("p2", "c2", "PB", "New"),
            status_row("p3", "c3", "VAN", "Inactive"),
        ])
        ledger = build(df, status)

        for grain in [None, ["chain"], ["sku"], ["chain", "sku"]]:
            agg = aggregate_units_contributions(ledger, group_cols=grain)
            gap = (agg["distribution_impact"] + agg["velocity_impact"] - agg["total_change"]).abs()
            assert (gap < 1e-6).all(), f"reconciliation failed at grain {grain}"

    def test_children_sum_to_parent(self):
        # the whole point of atom-level attribution: chains sum to business
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 130, chain="WF"),
            sales_row("p2", "c2", "PB", "2026-03", 80, chain="SPROUTS"),
            sales_row("p3", "c3", "VAN", "2026-01", 60, chain="KROGER"),
        ])
        status = make_status([
            status_row("p1", "c1", "VAN", "New"),
            status_row("p2", "c2", "PB", "New"),
            status_row("p3", "c3", "VAN", "Inactive"),
        ])
        ledger = build(df, status)
        business = aggregate_units_contributions(ledger, group_cols=None)
        by_chain = aggregate_units_contributions(ledger, group_cols=["chain"])

        for col in ["total_change", "distribution_impact", "velocity_impact"]:
            assert abs(by_chain[col].sum() - business[col].iloc[0]) < 1e-6, col

    def test_validate_helper_reports_zero_gap(self):
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-01", 100),
            sales_row("p1", "c1", "VAN", "2026-03", 130),
        ])
        status = make_status([status_row("p1", "c1", "VAN", "Healthy")])
        ledger = build(df, status)
        report = validate_contribution_reconciliation(ledger)
        assert abs(report["reconciliation_gap"]) < 1e-6


# =========================================================
# Status-as-of join
# =========================================================

class TestStatusJoin:

    def test_uses_latest_status_at_or_before_current_end(self):
        # status changes over time; join should pick the one <= current_end,
        # not an earlier or a future one.
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 120),
        ])
        status = make_status([
            status_row("p1", "c1", "VAN", "New", month="2026-01"),      # old
            status_row("p1", "c1", "VAN", "Healthy", month="2026-04"),  # as-of
            status_row("p1", "c1", "VAN", "Struggling", month="2026-06"),  # future, ignore
        ])
        out = build(df, status)
        assert out.iloc[0]["sku_status"] == "Healthy"

    def test_sparse_status_table_falls_back_to_prior_month(self):
        # no status row exactly at current_end; latest is 2026-02 -> use it
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 120),
        ])
        status = make_status([
            status_row("p1", "c1", "VAN", "New", month="2026-02"),
        ])
        out = build(df, status)
        assert out.iloc[0]["sku_status"] == "New"

    def test_future_only_status_leaves_row_unmatched_and_raises(self):
        # INTENT: if the ONLY status is after current_end, there is no valid
        # as-of status, so a moving row is unmatched and the tripwire fires.
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 120),
        ])
        status = make_status([
            status_row("p1", "c1", "VAN", "New", month="2026-06"),
        ])
        with pytest.raises(ValueError):
            build(df, status)


# =========================================================
# Tripwires
# =========================================================

class TestTripwires:

    def test_missing_status_for_mover_raises(self):
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 120),
        ])
        status = make_status([
            status_row("p2", "c2", "OTHER", "Healthy"),  # unrelated atom
        ])
        with pytest.raises(ValueError):
            build(df, status)

    def test_unmapped_status_raises(self):
        # a status string in neither DISTRIBUTION nor VELOCITY sets -> the
        # reconciliation tripwire should fire (impact goes to neither bucket).
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 120),
        ])
        status = make_status([status_row("p1", "c1", "VAN", "Zombie")])
        with pytest.raises(ValueError):
            build(df, status)

    def test_dash_status_for_mover_raises(self):
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 120),
        ])
        status = make_status([status_row("p1", "c1", "VAN", "-")])
        with pytest.raises(ValueError):
            build(df, status)

    def test_missing_month_year_column_raises(self):
        df = make_sales([sales_row("p1", "c1", "VAN", "2026-03", 120)])
        status = make_status([status_row("p1", "c1", "VAN", "New")]).drop(columns=["month_year"])
        with pytest.raises(ValueError):
            build(df, status)


# =========================================================
# Outer-join survival & non-mover handling
# =========================================================

class TestJoinSurvival:

    def test_lost_placement_survives(self):
        # prior only, nothing current -> row must survive as a negative mover
        df = make_sales([sales_row("p1", "c1", "VAN", "2026-01", 90)])
        status = make_status([status_row("p1", "c1", "VAN", "Inactive")])
        out = build(df, status)
        assert len(out) == 1
        assert out.iloc[0]["units_current"] == 0
        assert out.iloc[0]["units_prior"] == 90

    def test_non_mover_is_dropped(self):
        # same units both periods -> total_change 0 -> dropped
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-01", 100),
            sales_row("p1", "c1", "VAN", "2026-03", 100),
        ])
        status = make_status([status_row("p1", "c1", "VAN", "Healthy")])
        out = build(df, status)
        assert out.empty

    def test_out_of_window_sales_ignored(self):
        # a sale outside both windows should not affect anything
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-01", 100),
            sales_row("p1", "c1", "VAN", "2026-03", 130),
            sales_row("p1", "c1", "VAN", "2025-06", 999),   # ancient, ignored
        ])
        status = make_status([status_row("p1", "c1", "VAN", "Healthy")])
        out = build(df, status)
        assert out.iloc[0]["total_change"] == 30


# =========================================================
# Aggregation + driver classification
# =========================================================

class TestAggregation:

    def _ledger(self, rows_sales, rows_status):
        return build(make_sales(rows_sales), make_status(rows_status))

    def test_shares_sum_to_one_when_same_direction(self):
        # dist +60, vel +40, total +100 -> shares .6/.4
        led = self._ledger(
            [
                sales_row("p1", "c1", "PB", "2026-03", 60),               # New -> dist +60
                sales_row("p2", "c2", "VAN", "2026-01", 100, chain="X"),  # Healthy base
                sales_row("p2", "c2", "VAN", "2026-03", 140, chain="X"),  # +40 vel
            ],
            [
                status_row("p1", "c1", "PB", "New"),
                status_row("p2", "c2", "VAN", "Healthy"),
            ],
        )
        agg = aggregate_units_contributions(led, group_cols=None).iloc[0]
        assert agg["total_change"] == 100
        assert abs(agg["distribution_share"] - 0.6) < 1e-9
        assert abs(agg["velocity_share"] - 0.4) < 1e-9

    def test_offsetting_shares_exceed_one(self):
        # dist +120, vel -20, total +100 -> dist_share 1.2, vel_share -0.2
        led = self._ledger(
            [
                sales_row("p1", "c1", "PB", "2026-03", 120),              # New -> dist +120
                sales_row("p2", "c2", "VAN", "2026-01", 100, chain="X"),  # Healthy base
                sales_row("p2", "c2", "VAN", "2026-03", 80, chain="X"),   # -20 vel
            ],
            [
                status_row("p1", "c1", "PB", "New"),
                status_row("p2", "c2", "VAN", "Healthy"),
            ],
        )
        agg = aggregate_units_contributions(led, group_cols=None).iloc[0]
        assert agg["total_change"] == 100
        assert abs(agg["distribution_share"] - 1.2) < 1e-9
        assert abs(agg["velocity_share"] - (-0.2)) < 1e-9

    def test_primary_driver_distribution_when_offsetting(self):
        # same as above: distribution clearly led despite >100% share
        led = self._ledger(
            [
                sales_row("p1", "c1", "PB", "2026-03", 120),
                sales_row("p2", "c2", "VAN", "2026-01", 100, chain="X"),
                sales_row("p2", "c2", "VAN", "2026-03", 80, chain="X"),
            ],
            [
                status_row("p1", "c1", "PB", "New"),
                status_row("p2", "c2", "VAN", "Healthy"),
            ],
        )
        agg = aggregate_units_contributions(led, group_cols=None).iloc[0]
        assert agg["primary_driver"] == "distribution"

    def test_primary_driver_balanced_at_55_45(self):
        # INTENT: 55/45 split should be "balanced", not "distribution".
        # dist +55, vel +45, total +100 -> dominant share .55 < .65 -> balanced
        led = self._ledger(
            [
                sales_row("p1", "c1", "PB", "2026-03", 55),               # New dist +55
                sales_row("p2", "c2", "VAN", "2026-01", 100, chain="X"),  # Healthy base
                sales_row("p2", "c2", "VAN", "2026-03", 145, chain="X"),  # +45 vel
            ],
            [
                status_row("p1", "c1", "PB", "New"),
                status_row("p2", "c2", "VAN", "Healthy"),
            ],
        )
        agg = aggregate_units_contributions(led, group_cols=None).iloc[0]
        assert agg["total_change"] == 100
        assert agg["primary_driver"] == "balanced"

    def test_primary_driver_velocity_when_dominant(self):
        # vel +90, dist +10, total +100 -> velocity led
        led = self._ledger(
            [
                sales_row("p1", "c1", "PB", "2026-03", 10),               # New dist +10
                sales_row("p2", "c2", "VAN", "2026-01", 100, chain="X"),  # Healthy base
                sales_row("p2", "c2", "VAN", "2026-03", 190, chain="X"),  # +90 vel
            ],
            [
                status_row("p1", "c1", "PB", "New"),
                status_row("p2", "c2", "VAN", "Healthy"),
            ],
        )
        agg = aggregate_units_contributions(led, group_cols=None).iloc[0]
        assert agg["primary_driver"] == "velocity"

    def test_primary_driver_none_when_net_zero_group(self):
        # INTENT: a group whose members net to zero -> "none", shares NaN.
        # +50 (New dist) and -50 (Inactive dist) in the same chain.
        led = self._ledger(
            [
                sales_row("p1", "c1", "PB", "2026-03", 50, chain="X"),   # New +50
                sales_row("p2", "c2", "VAN", "2026-01", 50, chain="X"),  # Inactive -50
            ],
            [
                status_row("p1", "c1", "PB", "New"),
                status_row("p2", "c2", "VAN", "Inactive"),
            ],
        )
        agg = aggregate_units_contributions(led, group_cols=["chain"])
        row = agg[agg["chain"] == "X"].iloc[0]
        assert row["total_change"] == 0
        assert row["primary_driver"] == "none"
        assert pd.isna(row["distribution_share"])
        assert pd.isna(row["velocity_share"])


# =========================================================
# Null dimension handling
# =========================================================

class TestNullDimensions:

    def test_null_state_row_is_retained(self):
        # INTENT: rows with a null dimension value must NOT be silently
        # dropped (dropna=False). They should survive into the ledger so the
        # tree can fold them into a residual rather than lose the units.
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 70, state=None),
        ])
        status = make_status([status_row("p1", "c1", "VAN", "New")])
        out = build(df, status)
        assert len(out) == 1
        assert out.iloc[0]["total_change"] == 70

    def test_null_dimension_units_still_reconcile(self):
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-03", 70, state=None),
            sales_row("p2", "c2", "PB", "2026-03", 30, state="CA"),
        ])
        status = make_status([
            status_row("p1", "c1", "VAN", "New"),
            status_row("p2", "c2", "PB", "New"),
        ])
        led = build(df, status)
        business = aggregate_units_contributions(led, group_cols=None)
        by_state = aggregate_units_contributions(led, group_cols=["state"])
        assert abs(by_state["total_change"].sum() - business["total_change"].iloc[0]) < 1e-6


# =========================================================
# Empty / degenerate inputs
# =========================================================

class TestEmptyInputs:

    def test_empty_df_returns_empty_with_columns(self):
        status = make_status([status_row("p1", "c1", "VAN", "New")])
        out = build(pd.DataFrame(), status)
        assert out.empty
        for col in ATOM + ["distribution_impact", "velocity_impact", "total_change"]:
            assert col in out.columns

    def test_empty_status_returns_empty(self):
        df = make_sales([sales_row("p1", "c1", "VAN", "2026-03", 70)])
        out = build(df, pd.DataFrame())
        assert out.empty

    def test_aggregate_empty_returns_empty(self):
        assert aggregate_units_contributions(pd.DataFrame()).empty

    def test_wrapper_empty_returns_empty(self):
        status = make_status([status_row("p1", "c1", "VAN", "New")])
        out = calculate_units_growth_decomposition_additive(
            df=pd.DataFrame(), status_table=status,
            current_start=CURR_START, current_end=CURR_END,
            prior_start=PRIOR_START, prior_end=PRIOR_END,
            group_cols=["chain"],
        )
        assert out.empty

    def test_validate_empty_returns_zeroed_report(self):
        report = validate_contribution_reconciliation(pd.DataFrame())
        assert report["reconciliation_gap"] == 0
        assert report["total_change"] == 0


# =========================================================
# Wrapper end-to-end
# =========================================================

class TestWrapper:

    def test_wrapper_matches_manual_build_then_aggregate(self):
        df = make_sales([
            sales_row("p1", "c1", "VAN", "2026-01", 100, chain="WF"),
            sales_row("p1", "c1", "VAN", "2026-03", 130, chain="WF"),
            sales_row("p2", "c2", "PB", "2026-03", 80, chain="SPROUTS"),
        ])
        status = make_status([
            status_row("p1", "c1", "VAN", "Healthy"),
            status_row("p2", "c2", "PB", "New"),
        ])
        manual = aggregate_units_contributions(build(df, status), group_cols=["chain"])
        wrapped = calculate_units_growth_decomposition_additive(
            df=df, status_table=status,
            current_start=CURR_START, current_end=CURR_END,
            prior_start=PRIOR_START, prior_end=PRIOR_END,
            group_cols=["chain"],
        )
        pd.testing.assert_frame_equal(
            manual.sort_values("chain").reset_index(drop=True),
            wrapped.sort_values("chain").reset_index(drop=True),
        )
# ---------------------------------------------------------
# Additional edge cases I would add
# ---------------------------------------------------------



def test_multiple_transactions_inside_window_are_summed():
    df = make_sales([
        sales_row("p1", "c1", "VAN", "2026-02", 20),
        sales_row("p1", "c1", "VAN", "2026-03", 30),
        sales_row("p1", "c1", "VAN", "2026-04", 40),
    ])

    status = make_status([
        status_row("p1", "c1", "VAN", "New"),
    ])

    out = build(df, status)

    assert out.iloc[0]["units_current"] == 90
    assert out.iloc[0]["distribution_impact"] == 90


def test_struggling_positive_change_is_velocity():
    """
    Status determines the bucket, not the sign.
    """
    df = make_sales([
        sales_row("p1", "c1", "VAN", "2026-01", 40),
        sales_row("p1", "c1", "VAN", "2026-03", 55),
    ])

    status = make_status([
        status_row("p1", "c1", "VAN", "Struggling"),
    ])

    out = build(df, status)

    assert out.iloc[0]["total_change"] == 15
    assert out.iloc[0]["velocity_impact"] == 15
    assert out.iloc[0]["distribution_impact"] == 0


def test_inactive_with_zero_to_zero_does_not_appear():
    """
    Already inactive in both periods = no new contribution.
    """
    df = make_sales([
        # Some unrelated row so df isn't empty.
        sales_row("p2", "c2", "OTHER", "2026-03", 10),
    ])

    status = make_status([
        status_row("p1", "c1", "VAN", "Inactive"),
        status_row("p2", "c2", "OTHER", "New"),
    ])

    out = build(df, status)

    assert not (
        (out["coded_customer"] == "c1")
        & (out["sku"] == "VAN")
    ).any()


def test_exact_65_percent_is_distribution_led():
    """
    Current implementation uses < .65 for balanced,
    so exactly .65 counts as led.
    """
    led = build(
        make_sales([
            sales_row("p1", "c1", "PB", "2026-03", 65),
            sales_row("p2", "c2", "VAN", "2026-01", 100, chain="X"),
            sales_row("p2", "c2", "VAN", "2026-03", 135, chain="X"),
        ]),
        make_status([
            status_row("p1", "c1", "PB", "New"),
            status_row("p2", "c2", "VAN", "Healthy"),
        ]),
    )

    agg = aggregate_units_contributions(led).iloc[0]

    assert agg["distribution_share"] == pytest.approx(0.65)
    assert agg["primary_driver"] == "distribution"


def test_group_cols_string_and_list_match():
    df = make_sales([
        sales_row("p1", "c1", "VAN", "2026-03", 50, chain="WF"),
        sales_row("p2", "c2", "PB", "2026-03", 30, chain="SPROUTS"),
    ])

    status = make_status([
        status_row("p1", "c1", "VAN", "New"),
        status_row("p2", "c2", "PB", "New"),
    ])

    ledger = build(df, status)

    a = aggregate_units_contributions(ledger, group_cols="chain")
    b = aggregate_units_contributions(ledger, group_cols=["chain"])

    pd.testing.assert_frame_equal(
        a.sort_values("chain").reset_index(drop=True),
        b.sort_values("chain").reset_index(drop=True),
    )