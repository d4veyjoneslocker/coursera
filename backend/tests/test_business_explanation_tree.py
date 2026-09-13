import pandas as pd

from backend.insights.business_narrative.build_business_explanation_tree import (
    build_business_explanation_tree,
    compute_node_velocity,
)


# =========================================================
# Helpers
# =========================================================

CURRENT_START = pd.Period("2026-05", freq="M")
CURRENT_END = pd.Period("2026-07", freq="M")

PRIOR_START = pd.Period("2026-02", freq="M")
PRIOR_END = pd.Period("2026-04", freq="M")


def add_placement(
    rows,
    *,
    store,
    chain,
    sku,
    lifecycle,
    monthly_units,
):
    """
    Add one store x SKU placement across the supplied months.
    """

    pod_helper = f"{store}_{sku}"

    first_month = min(
        pd.Period(month, freq="M")
        for month in monthly_units
        if monthly_units[month] > 0
    )

    for month, units in monthly_units.items():
        month_period = pd.Period(month, freq="M")

        rows.append({
            "month_year": month_period,
            "coded_customer": store,
            "chain": chain,
            "sku": sku,
            "dc": "TEST_DC",
            "state": "TEST_STATE",

            "pod_helper": pod_helper,
            "sku_lifecycle": lifecycle,
            "sku_first_month_purchased": first_month,

            "units": units,

            # Needed by ramping metric code if tree reaches it.
            "reorder_flag_pod": 0,
        })


def find_driver(tree, driver_type):
    return next(
        child
        for child in tree.children
        if child.driver_type == driver_type
    )


def find_child(node, **scope):
    for child in node.children:
        if child.node_type != "entity":
            continue

        if all(
            child.scope.get(key) == value
            for key, value in scope.items()
        ):
            return child

    raise AssertionError(
        f"Could not find child with scope={scope}"
    )


# =========================================================
# Test 1
#
# compute_node_velocity:
# same mature cohort, correct scope, ignores ramping
# =========================================================

def test_compute_node_velocity_mature_cohort_only():
    rows = []

    mature_units = {
        "2026-02": 4,
        "2026-03": 4,
        "2026-04": 5,
        "2026-05": 8,
        "2026-06": 8,
        "2026-07": 10,
    }

    add_placement(
        rows,
        store="STORE_A",
        chain="TEST CHAIN",
        sku="TEST SKU",
        lifecycle="Mature",
        monthly_units=mature_units,
    )

    add_placement(
        rows,
        store="STORE_B",
        chain="TEST CHAIN",
        sku="TEST SKU",
        lifecycle="Mature",
        monthly_units=mature_units,
    )

    # Huge ramping decline: must not contaminate mature VPO.
    add_placement(
        rows,
        store="STORE_C",
        chain="TEST CHAIN",
        sku="TEST SKU",
        lifecycle="Ramping",
        monthly_units={
            "2026-02": 1000,
            "2026-03": 1000,
            "2026-04": 1000,
            "2026-05": 1,
            "2026-06": 1,
            "2026-07": 1,
        },
    )

    # Huge mature decline, but outside node scope.
    add_placement(
        rows,
        store="STORE_D",
        chain="OTHER CHAIN",
        sku="TEST SKU",
        lifecycle="Mature",
        monthly_units={
            "2026-02": 500,
            "2026-03": 500,
            "2026-04": 500,
            "2026-05": 1,
            "2026-06": 1,
            "2026-07": 1,
        },
    )

    df = pd.DataFrame(rows)

    rate_current, rate_prior, rate_change = compute_node_velocity(
        df=df,
        scope={"chain": "TEST CHAIN"},
        current_end=CURRENT_END,
        prior_end=PRIOR_END,
    )

    expected_prior = 26 / 2 / 12
    expected_current = 52 / 2 / 12
    expected_change = 1.0

    assert abs(rate_prior - expected_prior) < 1e-9
    assert abs(rate_current - expected_current) < 1e-9
    assert abs(rate_change - expected_change) < 1e-9


# =========================================================
# Test 2
#
# Full explanation-tree integration:
# mature driver gets expected VPO metadata
# =========================================================

def test_tree_attaches_correct_mature_driver_velocity():
    rows = []

    # Mature cohort:
    # prior = 26 total units
    # current = 52 total units
    # => +100% VPO
    mature_units = {
        "2026-02": 4,
        "2026-03": 4,
        "2026-04": 5,
        "2026-05": 8,
        "2026-06": 8,
        "2026-07": 10,
    }

    add_placement(
        rows,
        store="STORE_A",
        chain="MATURE CHAIN",
        sku="SKU_A",
        lifecycle="Mature",
        monthly_units=mature_units,
    )

    add_placement(
        rows,
        store="STORE_B",
        chain="MATURE CHAIN",
        sku="SKU_A",
        lifecycle="Mature",
        monthly_units=mature_units,
    )

    # Add some New contribution so total business change is comfortably
    # above the default magnitude gate.
    add_placement(
        rows,
        store="STORE_NEW",
        chain="NEW CHAIN",
        sku="SKU_NEW",
        lifecycle="New",
        monthly_units={
            "2026-02": 0,
            "2026-03": 0,
            "2026-04": 0,
            "2026-05": 250,
            "2026-06": 250,
            "2026-07": 250,
        },
    )

    df = pd.DataFrame(rows)

    tree = build_business_explanation_tree(
        df=df,
        current_start=CURRENT_START,
        current_end=CURRENT_END,
        prior_start=PRIOR_START,
        prior_end=PRIOR_END,
        magnitude_gate=1,
        magnitude_floor=1,
        min_child_impact=1,
    )

    mature = find_driver(
        tree,
        "mature",
    )

    expected_prior = 26 / 2 / 12
    expected_current = 52 / 2 / 12
    expected_change = 1.0

    assert abs(mature.rate_prior - expected_prior) < 1e-9
    assert abs(mature.rate_current - expected_current) < 1e-9
    assert abs(mature.rate_change - expected_change) < 1e-9


# =========================================================
# Test 3
#
# Full tree:
# child mature scope gets its own correct velocity
# =========================================================

def test_tree_attaches_scope_specific_mature_velocity():
    rows = []

    # ---------------------------------------------------------
    # Chain A = +100% VPO
    #
    # Prior per store:
    #   400 + 400 + 500 = 1,300
    #
    # Current per store:
    #   800 + 800 + 1,000 = 2,600
    #
    # => +100%
    #
    # With 2 stores:
    #   prior total   = 2,600
    #   current total = 5,200
    #   unit impact   = +2,600
    # ---------------------------------------------------------

    for store in ["A1", "A2"]:
        add_placement(
            rows,
            store=store,
            chain="CHAIN A",
            sku="SKU_A",
            lifecycle="Mature",
            monthly_units={
                "2026-02": 400,
                "2026-03": 400,
                "2026-04": 500,
                "2026-05": 800,
                "2026-06": 800,
                "2026-07": 1000,
            },
        )

    # ---------------------------------------------------------
    # Chain B = -50% VPO
    #
    # Prior per store:
    #   200 + 200 + 200 = 600
    #
    # Current per store:
    #   100 + 100 + 100 = 300
    #
    # => -50%
    #
    # With 2 stores:
    #   prior total   = 1,200
    #   current total = 600
    #   unit impact   = -600
    #
    # Mature net impact = +2,000
    # ---------------------------------------------------------

    for store in ["B1", "B2"]:
        add_placement(
            rows,
            store=store,
            chain="CHAIN B",
            sku="SKU_B",
            lifecycle="Mature",
            monthly_units={
                "2026-02": 200,
                "2026-03": 200,
                "2026-04": 200,
                "2026-05": 100,
                "2026-06": 100,
                "2026-07": 100,
            },
        )

    # ---------------------------------------------------------
    # Add a New branch so the full business tree still contains
    # another lifecycle bucket, but keep it small enough that
    # Mature remains a meaningful share of the business.
    #
    # New impact = +900
    # ---------------------------------------------------------

    add_placement(
        rows,
        store="NEW1",
        chain="NEW CHAIN",
        sku="SKU_NEW",
        lifecycle="New",
        monthly_units={
            "2026-02": 0,
            "2026-03": 0,
            "2026-04": 0,
            "2026-05": 300,
            "2026-06": 300,
            "2026-07": 300,
        },
    )

    df = pd.DataFrame(rows)

    tree = build_business_explanation_tree(
        df=df,
        current_start=CURRENT_START,
        current_end=CURRENT_END,
        prior_start=PRIOR_START,
        prior_end=PRIOR_END,
        magnitude_gate=1,
        magnitude_floor=1,
        min_child_impact=1,
        concentration_gate=0.0,
    )

    mature = find_driver(
        tree,
        "mature",
    )

    chain_a = find_child(
        mature,
        chain="CHAIN A",
    )

    chain_b = find_child(
        mature,
        chain="CHAIN B",
    )

    # ---------------------------------------------------------
    # Validate scope-specific mature velocity
    # ---------------------------------------------------------

    assert abs(chain_a.rate_change - 1.0) < 1e-9
    assert abs(chain_b.rate_change - (-0.5)) < 1e-9

    print(
        "CHAIN A:",
        chain_a.rate_prior,
        chain_a.rate_current,
        chain_a.rate_change,
    )

    print(
        "CHAIN B:",
        chain_b.rate_prior,
        chain_b.rate_current,
        chain_b.rate_change,
    )


# =========================================================
# Test 4
#
# No mature rows -> velocity should be None
# =========================================================

def test_compute_node_velocity_returns_none_without_mature_rows():
    rows = []

    add_placement(
        rows,
        store="STORE_A",
        chain="TEST CHAIN",
        sku="TEST SKU",
        lifecycle="Ramping",
        monthly_units={
            "2026-02": 10,
            "2026-03": 10,
            "2026-04": 10,
            "2026-05": 10,
            "2026-06": 10,
            "2026-07": 10,
        },
    )

    df = pd.DataFrame(rows)

    rate_current, rate_prior, rate_change = compute_node_velocity(
        df=df,
        scope={"chain": "TEST CHAIN"},
        current_end=CURRENT_END,
        prior_end=PRIOR_END,
    )

    assert rate_current is None
    assert rate_prior is None
    assert rate_change is None


# =========================================================
# Test 5
#
# Mature cohort exists only in current period:
# no valid prior VPO => rate_change must be None
# =========================================================

def test_compute_node_velocity_returns_none_without_prior_baseline():
    rows = []

    add_placement(
        rows,
        store="STORE_A",
        chain="TEST CHAIN",
        sku="TEST SKU",
        lifecycle="Mature",
        monthly_units={
            "2026-02": 0,
            "2026-03": 0,
            "2026-04": 0,
            "2026-05": 10,
            "2026-06": 10,
            "2026-07": 10,
        },
    )

    df = pd.DataFrame(rows)

    rate_current, rate_prior, rate_change = compute_node_velocity(
        df=df,
        scope={"chain": "TEST CHAIN"},
        current_end=CURRENT_END,
        prior_end=PRIOR_END,
    )

    assert rate_current is not None

    # Depending on calculate_vpo_3m's treatment of no prior buyers,
    # prior may be NaN or None. The important contract is that growth
    # cannot be calculated against a zero / missing baseline.
    assert (
        rate_prior is None
        or pd.isna(rate_prior)
        or rate_prior == 0
    )

    assert rate_change is None


# =========================================================
# Test 6
#
# Flat mature cohort -> 0% change
# =========================================================

def test_compute_node_velocity_flat_mature_cohort():
    rows = []

    for store in ["STORE_A", "STORE_B"]:
        add_placement(
            rows,
            store=store,
            chain="TEST CHAIN",
            sku="TEST SKU",
            lifecycle="Mature",
            monthly_units={
                "2026-02": 5,
                "2026-03": 5,
                "2026-04": 5,
                "2026-05": 5,
                "2026-06": 5,
                "2026-07": 5,
            },
        )

    df = pd.DataFrame(rows)

    rate_current, rate_prior, rate_change = compute_node_velocity(
        df=df,
        scope={"chain": "TEST CHAIN"},
        current_end=CURRENT_END,
        prior_end=PRIOR_END,
    )

    assert rate_prior is not None
    assert rate_current is not None
    assert abs(rate_change) < 1e-9


# =========================================================
# Simple runner
# =========================================================

if __name__ == "__main__":
    tests = [
        test_compute_node_velocity_mature_cohort_only,
        test_tree_attaches_correct_mature_driver_velocity,
        test_tree_attaches_scope_specific_mature_velocity,
        test_compute_node_velocity_returns_none_without_mature_rows,
        test_compute_node_velocity_returns_none_without_prior_baseline,
        test_compute_node_velocity_flat_mature_cohort,
    ]

    for test in tests:
        print(f"\nRunning {test.__name__}...")
        test()
        print("✅ passed")

    print("\n✅ All mature velocity tests passed")

def test_compute_node_velocity_uses_full_six_month_period():
    """
    Explicit 6-month bounds must use the entire requested period,
    not silently fall back to the last 3 months.

    Prior H1 per store:
        Jan-Jun = 10 units/month = 60 total

    Current H1 per store:
        Jan-Mar = 5 units/month
        Apr-Jun = 15 units/month
        = 60 total

    Therefore full-period VPO is unchanged => 0% change.

    But if the calculation incorrectly used only the final 3 months:
        prior Apr-Jun = 30
        current Apr-Jun = 45
        => +50%

    So this test distinguishes full-H1 velocity from old L3M behavior.
    """

    rows = []

    for store in ["STORE_A", "STORE_B"]:
        add_placement(
            rows,
            store=store,
            chain="TEST CHAIN",
            sku="TEST SKU",
            lifecycle="Mature",
            monthly_units={
                # Prior H1
                "2025-01": 10,
                "2025-02": 10,
                "2025-03": 10,
                "2025-04": 10,
                "2025-05": 10,
                "2025-06": 10,

                # Current H1
                "2026-01": 5,
                "2026-02": 5,
                "2026-03": 5,
                "2026-04": 15,
                "2026-05": 15,
                "2026-06": 15,
            },
        )

    df = pd.DataFrame(rows)

    rate_current, rate_prior, rate_change = compute_node_velocity(
        df=df,
        scope={"chain": "TEST CHAIN"},
        current_start=pd.Period("2026-01", freq="M"),
        current_end=pd.Period("2026-06", freq="M"),
        prior_start=pd.Period("2025-01", freq="M"),
        prior_end=pd.Period("2025-06", freq="M"),
    )

    # Both periods:
    # 120 total units / 2 stores / 24 weeks
    expected_vpo = 120 / 2 / 24

    assert abs(rate_prior - expected_vpo) < 1e-9
    assert abs(rate_current - expected_vpo) < 1e-9
    assert abs(rate_change) < 1e-9