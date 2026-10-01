import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)

from backend.metrics.features import calculate_store_sku_lifecycle
from backend.metrics.metric_callers import calculate_metric
from backend.metrics.metric_helpers import filter_to_period


def calculate_dc_weekly_velocity(
    features_df: pd.DataFrame,
    active_pods_df: pd.DataFrame,
    overrides_df: pd.DataFrame | None = None,
    store_col: str = "coded_customer",
    month_col: str = "month_year",
    first_month_col: str = "sku_first_month_purchased",
    as_of_month: pd.Period | None = None,
) -> pd.DataFrame:
    df = features_df.copy()

    df = features_df.copy()

    # Normally velocity runs through the latest completed month.
    # For historical analysis, as_of_month explicitly becomes that completed month.
    current_month = (as_of_month + 1) if as_of_month is not None else pd.Timestamp.today().to_period("M")
    complete_end = current_month - 1

    # Historical runs must not see data after the requested month.
    if as_of_month is not None:
        df = df[df[month_col] <= as_of_month].copy()

    # Current calendar month is excluded from direct velocity calculations.
    df_complete = df[df[month_col] <= complete_end].copy()

    # Lifecycle is anchored to the latest completed 3-month window.
    current_start = complete_end - 2
    prior_start = current_start - 3

    lifecycle = calculate_store_sku_lifecycle(
        df,
        current_start=current_start,
        prior_start=prior_start,
        current_end=complete_end,
    )

    df = df.merge(
        lifecycle[["pod_helper", "sku_lifecycle"]],
        on="pod_helper",
        how="left",
    )

    df_complete = df_complete.merge(
        lifecycle[["pod_helper", "sku_lifecycle"]],
        on="pod_helper",
        how="left",
    )

    store_keys = ["distributor", "sku", store_col]

    # Current store-SKU population uses ALL data, including the partial current month.
    # This is what allows brand-new stores this month to enter inventory demand.
    latest = (
    df.sort_values(month_col)
        .groupby(store_keys, as_index=False)
        .tail(1)
    )

    latest = latest[
        store_keys + ["dc", "chain", "channel", "sku_lifecycle", month_col]
    ].copy()

    # Mature store-SKUs must have purchased within the latest 3 complete months
    recent_start = complete_end - 2

    latest = latest[
        latest["sku_lifecycle"].ne("Mature")
        | latest[month_col].between(recent_start, complete_end)
    ].copy()

    # -------------------------------------------------------------------------
    # MATURE
    # Latest 3 COMPLETE months only.
    # -------------------------------------------------------------------------

    mature_df = df_complete[
        df_complete["sku_lifecycle"].eq("Mature")
        & df_complete[month_col].between(current_start, complete_end)
    ].copy()

    mature_active_pods = active_pods_df[
        active_pods_df["pod_helper"].isin(mature_df["pod_helper"])
    ].copy()

    mature_active_pods = filter_to_period(
        mature_active_pods,
        current_start,
        complete_end,
    )

    mature_vpo = calculate_metric(
        metric_name="velocity",
        df_filtered=mature_df,
        active_pods_df=mature_active_pods,
        group_cols=store_keys,
    ).rename(columns={"value": "planning_vpo"})

    mature_vpo["planning_vpo_source"] = "mature_l3m"

    # -------------------------------------------------------------------------
    # RAMPING
    # Ignore first 3 months after launch.
    # Then use 1, 2, or 3 COMPLETE eligible months depending on availability.
    # -------------------------------------------------------------------------

    ramping = df_complete[
        df_complete["sku_lifecycle"].eq("Ramping")
    ].copy()

    ramping["eligible_start"] = ramping[first_month_col] + 3

    ramping["eligible_months"] = (
        complete_end.ordinal
        - ramping["eligible_start"].astype("int64")
        + 1
    ).clip(lower=0, upper=3)

    ramping_results = []

    for month_count in [1, 2, 3]:
        ramping_group = ramping[
            ramping["eligible_months"].eq(month_count)
        ].copy()

        if ramping_group.empty:
            continue

        start_period = complete_end - (month_count - 1)

        ramping_group = ramping_group[
            ramping_group[month_col].between(start_period, complete_end)
        ].copy()

        ramping_active_pods = active_pods_df[
            active_pods_df["pod_helper"].isin(ramping_group["pod_helper"])
        ].copy()

        ramping_active_pods = filter_to_period(
            ramping_active_pods,
            start_period,
            complete_end,
        )

        result = calculate_metric(
            metric_name="velocity",
            df_filtered=ramping_group,
            active_pods_df=ramping_active_pods,
            group_cols=store_keys,
        ).rename(columns={"value": "planning_vpo"})

        ramping_results.append(result)

    if ramping_results:
        ramping_vpo = pd.concat(ramping_results, ignore_index=True)
        ramping_vpo["planning_vpo_source"] = "ramping_post_launch"
    else:
        ramping_vpo = pd.DataFrame(
            columns=store_keys + ["planning_vpo", "planning_vpo_source"]
        )

    # -------------------------------------------------------------------------
    # BUILD STORE-LEVEL PLANNING TABLE
    # -------------------------------------------------------------------------

    planning = latest.copy()

    planning = planning.merge(
        mature_vpo,
        on=store_keys,
        how="left",
    )

    planning = planning.merge(
        ramping_vpo,
        on=store_keys,
        how="left",
        suffixes=("", "_ramping"),
    )

    planning["planning_vpo"] = planning["planning_vpo"].fillna(
        planning["planning_vpo_ramping"]
    )

    planning["planning_vpo_source"] = planning["planning_vpo_source"].fillna(
        planning["planning_vpo_source_ramping"]
    )

    planning = planning.drop(
        columns=[
            "planning_vpo_ramping",
            "planning_vpo_source_ramping",
        ]
    )

    # Mature + Ramping stores with usable velocity become the benchmark pool.
    benchmark_stores = planning[
        planning["planning_vpo"].notna()
    ].copy()

    # -------------------------------------------------------------------------
    # NEW STORE BENCHMARKS
    # -------------------------------------------------------------------------

    chain_benchmark = (
        benchmark_stores
        .groupby(
            ["distributor", "chain", "sku"],
            as_index=False,
        )["planning_vpo"]
        .mean()
        .rename(columns={"planning_vpo": "chain_sku_vpo"})
    )

    channel_benchmark = (
        benchmark_stores
        .groupby(
            ["distributor", "channel", "sku"],
            as_index=False,
        )["planning_vpo"]
        .mean()
        .rename(columns={"planning_vpo": "channel_sku_vpo"})
    )

    sku_benchmark = (
        benchmark_stores
        .groupby(
            ["distributor", "sku"],
            as_index=False,
        )["planning_vpo"]
        .mean()
        .rename(columns={"planning_vpo": "sku_vpo"})
    )

    company_benchmark = benchmark_stores["planning_vpo"].mean()

    planning = planning.merge(
        chain_benchmark,
        on=["distributor", "chain", "sku"],
        how="left",
    )

    planning = planning.merge(
        channel_benchmark,
        on=["distributor", "channel", "sku"],
        how="left",
    )

    planning = planning.merge(
        sku_benchmark,
        on=["distributor", "sku"],
        how="left",
    )

    # -------------------------------------------------------------------------
    # NEW FALLBACK HIERARCHY
    #
    # Current-month launches are included here even though their current-month
    # sales were deliberately excluded from all VPO calculations.
    # -------------------------------------------------------------------------

    chain_mask = planning["planning_vpo"].isna() & planning["chain_sku_vpo"].notna()
    planning.loc[chain_mask, "planning_vpo"] = planning.loc[chain_mask, "chain_sku_vpo"]
    planning.loc[chain_mask, "planning_vpo_source"] = "chain_sku_benchmark"

    channel_mask = planning["planning_vpo"].isna() & planning["channel_sku_vpo"].notna()
    planning.loc[channel_mask, "planning_vpo"] = planning.loc[channel_mask, "channel_sku_vpo"]
    planning.loc[channel_mask, "planning_vpo_source"] = "channel_sku_benchmark"

    sku_mask = planning["planning_vpo"].isna() & planning["sku_vpo"].notna()
    planning.loc[sku_mask, "planning_vpo"] = planning.loc[sku_mask, "sku_vpo"]
    planning.loc[sku_mask, "planning_vpo_source"] = "sku_benchmark"

    company_mask = planning["planning_vpo"].isna() & pd.notna(company_benchmark)
    planning.loc[company_mask, "planning_vpo"] = company_benchmark
    planning.loc[company_mask, "planning_vpo_source"] = "company_benchmark"

    # -------------------------------------------------------------------------
    # USER OVERRIDES
    # -------------------------------------------------------------------------

    if overrides_df is not None and not overrides_df.empty:
        overrides = overrides_df[
            store_keys + ["planning_vpo"]
        ].rename(
            columns={"planning_vpo": "override_vpo"}
        )

        planning = planning.merge(
            overrides,
            on=store_keys,
            how="left",
        )

        override_mask = planning["override_vpo"].notna()

        planning.loc[
            override_mask,
            "planning_vpo",
        ] = planning.loc[
            override_mask,
            "override_vpo",
        ]

        planning.loc[
            override_mask,
            "planning_vpo_source",
        ] = "user_override"

        planning = planning.drop(columns=["override_vpo"])

    missing = planning[planning["planning_vpo"].isna()].copy()

    if planning["planning_vpo"].isna().any():
        raise ValueError(
            "Not enough sales history to calculate inventory velocity. "
            "More sales data is required."
        )

    # If there is no reasonable historical benchmark, don't invent one.
    if planning["planning_vpo"].isna().any():
        raise ValueError(
            "Not enough sales history to calculate inventory velocity. "
            "More sales data is required."
        )

    planning["is_provisional_velocity"] = planning[
        "planning_vpo_source"
    ].isin(
        [
            "chain_sku_benchmark",
            "channel_sku_benchmark",
            "sku_benchmark",
            "company_benchmark",
        ]
    )

    debug = planning[
        (planning["distributor"] == "UNFI")
        & (planning["dc"] == "HOW")
        & (planning["sku"] == "VANILLA BEAN")
    ].copy()

    # -------------------------------------------------------------------------
    # DC WEEKLY VELOCITY
    # -------------------------------------------------------------------------

    dc_velocity = (
        planning
        .groupby(
            ["distributor", "dc", "sku"],
            as_index=False,
        )
        .agg(
            dc_weekly_velocity=("planning_vpo", "sum"),
            provisional_store_count=("is_provisional_velocity", "sum"),
        )
    )

    dc_velocity["has_provisional_velocity"] = (
        dc_velocity["provisional_store_count"].gt(0)
    )

    return dc_velocity