import pandas as pd

from backend.insights.insights_helper import _build_3m_metrics
from backend.insights.diagnostics import calculate_units_growth_decomposition


# ---------------------------------------------------------
# Overall business
# ---------------------------------------------------------

def build_overall_analysis(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Builds L3M performance and growth metrics
    across the full business.
    """

    return _build_3m_metrics(
        df_filtered=df,
        df_full=df,
        grain=[],
    )


# ---------------------------------------------------------
# SKU
# ---------------------------------------------------------

def build_sku_analysis(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Builds L3M performance and growth metrics
    by SKU across the full business.
    """

    return _build_3m_metrics(
        df_filtered=df,
        df_full=df,
        grain=["sku"],
    )


# ---------------------------------------------------------
# Retailer
# ---------------------------------------------------------

def build_retailer_analysis(
    df: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Builds L3M performance and growth metrics
    for the largest retailers in the business.
    """

    result = _build_3m_metrics(
        df_filtered=df,
        df_full=df,
        grain=["chain"],
    )

    if result.empty:
        return result

    return (
        result
        .sort_values(
            "revenue_3m",
            ascending=False,
        )
        .head(top_n)
        .copy()
    )


# ---------------------------------------------------------
# State
# ---------------------------------------------------------

def build_state_analysis(
    df: pd.DataFrame,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Builds L3M performance and growth metrics
    for the largest states in the business.
    """

    result = _build_3m_metrics(
        df_filtered=df,
        df_full=df,
        grain=["state"],
    )

    if result.empty:
        return result

    return (
        result
        .sort_values(
            "revenue_3m",
            ascending=False,
        )
        .head(top_n)
        .copy()
    )


# ---------------------------------------------------------
# Retailer × SKU
# ---------------------------------------------------------

def build_retailer_sku_analysis(
    df: pd.DataFrame,
    top_n_retailers: int = 10,
) -> pd.DataFrame:
    """
    Builds SKU-level performance for the
    largest retailers in the business.
    """

    retailer_analysis = build_retailer_analysis(
        df=df,
        top_n=top_n_retailers,
    )

    if retailer_analysis.empty:
        return pd.DataFrame()

    top_retailers = (
        retailer_analysis["chain"]
        .dropna()
        .tolist()
    )

    df_filtered = df[
        df["chain"].isin(top_retailers)
    ].copy()

    return _build_3m_metrics(
        df_filtered=df_filtered,
        df_full=df_filtered,
        grain=["chain", "sku"],
    )


# ---------------------------------------------------------
# State × SKU
# ---------------------------------------------------------

def build_state_sku_analysis(
    df: pd.DataFrame,
    top_n_states: int = 5,
) -> pd.DataFrame:
    """
    Builds SKU-level performance for the
    largest states in the business.
    """

    state_analysis = build_state_analysis(
        df=df,
        top_n=top_n_states,
    )

    if state_analysis.empty:
        return pd.DataFrame()

    top_states = (
        state_analysis["state"]
        .dropna()
        .tolist()
    )

    df_filtered = df[
        df["state"].isin(top_states)
    ].copy()

    return _build_3m_metrics(
        df_filtered=df_filtered,
        df_full=df_filtered,
        grain=["state", "sku"],
    )


# ---------------------------------------------------------
# Master business analysis
# ---------------------------------------------------------

def build_business_analysis(
    df: pd.DataFrame,
    top_n_retailers: int = 10,
    top_n_states: int = 5,
) -> dict:
    """
    Builds the full evidence set used to identify
    positive business-level insights.
    """

    if df is None or df.empty:
        return {}

    return {
        "overall": build_overall_analysis(
            df=df,
        ),

        "sku": build_sku_analysis(
            df=df,
        ),

        "retailer": build_retailer_analysis(
            df=df,
            top_n=top_n_retailers,
        ),

        "state": build_state_analysis(
            df=df,
            top_n=top_n_states,
        ),

        "retailer_sku": build_retailer_sku_analysis(
            df=df,
            top_n_retailers=top_n_retailers,
        ),

        "state_sku": build_state_sku_analysis(
            df=df,
            top_n_states=top_n_states,
        ),
    }


# ---------------------------------------------------------
# Positive insight detection
# ---------------------------------------------------------

import pandas as pd


def build_business_signals(
    analysis: dict,
    growth_threshold: float = 0.10,
    velocity_threshold: float = 0.10,
    distribution_threshold: float = 0.15,
    comparison_threshold: float = 0.10,
    min_buying_stores: int = 10,
) -> list[dict]:
    """
    Converts business analysis tables into structured signals.

    This layer does NOT interpret the business meaning or write insight copy.
    It identifies notable positive / negative / neutral patterns and preserves
    the evidence needed for downstream interpretation.
    """

    signals = []

    if not analysis:
        return signals

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def valid_number(value):
        return pd.notna(value)

    def build_scope(
        row: pd.Series,
        scope_type: str,
    ) -> dict:

        scope = {}

        if "chain" in row.index and pd.notna(row["chain"]):
            scope["chain"] = row["chain"]

        if "state" in row.index and pd.notna(row["state"]):
            scope["state"] = row["state"]

        if "sku" in row.index and pd.notna(row["sku"]):
            scope["sku"] = row["sku"]

        return {
            "scope_type": scope_type,
            "scope": scope,
        }

    def get_scale(row: pd.Series) -> dict:
        scale = {}

        for col in [
            "revenue_3m",
            "units_3m",
            "buying_stores_3m",
            "vpo_3m",
        ]:
            if col in row.index and valid_number(row[col]):
                scale[col] = row[col]

        return scale

    # -----------------------------------------------------
    # Get total business buying stores
    # -----------------------------------------------------

    overall_df = analysis.get("overall")

    total_buying_stores = 0

    if (
        overall_df is not None
        and not overall_df.empty
        and "buying_stores_3m" in overall_df.columns
        and pd.notna(overall_df.iloc[0]["buying_stores_3m"])
    ):
        total_buying_stores = overall_df.iloc[0]["buying_stores_3m"]

    # -----------------------------------------------------
    # Signal strength
    # -----------------------------------------------------

    def calculate_strength(
        magnitude: float,
        buying_stores: float | None,
    ) -> float:
        """
        V1 signal strength:

        - magnitude_score = size of the signal
        - scale_score = share of total business buying stores represented

        Both are normalized to 0–1.
        """

        magnitude_score = min(
            abs(magnitude) / 0.50,
            1.0,
        )

        if (
            buying_stores is None
            or pd.isna(buying_stores)
            or total_buying_stores == 0
        ):
            scale_score = 0.0

        else:
            scale_score = min(
                buying_stores / total_buying_stores,
                1.0,
            )

        return round(
            (0.7 * magnitude_score)
            + (0.3 * scale_score),
            3,
        )

    def add_signal(
        *,
        signal_type: str,
        direction: str,
        scope_type: str,
        row: pd.Series,
        metrics: dict,
        magnitude: float,
        benchmark: dict | None = None,
    ):

        buying_stores = row.get(
            "buying_stores_3m",
            None,
        )

        signals.append(
            {
                "signal_type": signal_type,
                "direction": direction,

                **build_scope(
                    row=row,
                    scope_type=scope_type,
                ),

                "metrics": metrics,

                "benchmark": benchmark,

                "scale": get_scale(row),

                "strength": calculate_strength(
                    magnitude=magnitude,
                    buying_stores=buying_stores,
                ),
            }
        )

    # -----------------------------------------------------
    # Analysis configuration
    # -----------------------------------------------------

    scope_config = {
        "overall": "business",
        "sku": "sku",
        "retailer": "retailer",
        "state": "state",
        "retailer_sku": "retailer_sku",
        "state_sku": "state_sku",
    }

    # -----------------------------------------------------
    # 1. Growth / decline signals
    # -----------------------------------------------------

    for analysis_key, scope_type in scope_config.items():

        df = analysis.get(analysis_key)

        if df is None or df.empty:
            continue

        for _, row in df.iterrows():

            buying_stores = row.get(
                "buying_stores_3m",
                None,
            )

            # Ignore tiny slices except overall business
            if (
                scope_type != "business"
                and valid_number(buying_stores)
                and buying_stores < min_buying_stores
            ):
                continue

            revenue_growth = row.get(
                "revenue_l3m_pct"
            )

            units_growth = row.get(
                "units_l3m_pct"
            )

            store_growth = row.get(
                "buying_stores_l3m_pct"
            )

            vpo_growth = row.get(
                "vpo_l3m_pct"
            )

            # ---------------------------------------------
            # Revenue growth / decline
            # ---------------------------------------------

            if (
                valid_number(revenue_growth)
                and revenue_growth >= growth_threshold
            ):
                add_signal(
                    signal_type="revenue_growth",
                    direction="positive",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "revenue_l3m_pct":
                            revenue_growth,
                    },
                    magnitude=revenue_growth,
                )

            elif (
                valid_number(revenue_growth)
                and revenue_growth <= -growth_threshold
            ):
                add_signal(
                    signal_type="revenue_decline",
                    direction="negative",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "revenue_l3m_pct":
                            revenue_growth,
                    },
                    magnitude=revenue_growth,
                )

            # ---------------------------------------------
            # Unit growth / decline
            # ---------------------------------------------

            if (
                valid_number(units_growth)
                and units_growth >= growth_threshold
            ):
                add_signal(
                    signal_type="unit_growth",
                    direction="positive",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "units_l3m_pct":
                            units_growth,
                    },
                    magnitude=units_growth,
                )

            elif (
                valid_number(units_growth)
                and units_growth <= -growth_threshold
            ):
                add_signal(
                    signal_type="unit_decline",
                    direction="negative",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "units_l3m_pct":
                            units_growth,
                    },
                    magnitude=units_growth,
                )

            # ---------------------------------------------
            # Distribution expansion / contraction
            # ---------------------------------------------

            if (
                valid_number(store_growth)
                and store_growth >= distribution_threshold
            ):
                add_signal(
                    signal_type="distribution_expansion",
                    direction="positive",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "buying_stores_l3m_pct":
                            store_growth,
                        "units_l3m_pct":
                            units_growth,
                        "revenue_l3m_pct":
                            revenue_growth,
                        "vpo_l3m_pct":
                            vpo_growth,
                    },
                    magnitude=store_growth,
                )

            elif (
                valid_number(store_growth)
                and store_growth <= -distribution_threshold
            ):
                add_signal(
                    signal_type="distribution_contraction",
                    direction="negative",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "buying_stores_l3m_pct":
                            store_growth,
                        "units_l3m_pct":
                            units_growth,
                        "revenue_l3m_pct":
                            revenue_growth,
                    },
                    magnitude=store_growth,
                )

            # ---------------------------------------------
            # Velocity growth / pressure
            # ---------------------------------------------

            if (
                valid_number(vpo_growth)
                and vpo_growth >= velocity_threshold
            ):
                add_signal(
                    signal_type="velocity_growth",
                    direction="positive",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "vpo_l3m_pct":
                            vpo_growth,
                    },
                    magnitude=vpo_growth,
                )

            elif (
                valid_number(vpo_growth)
                and vpo_growth <= -velocity_threshold
            ):
                add_signal(
                    signal_type="velocity_pressure",
                    direction="negative",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "vpo_l3m_pct":
                            vpo_growth,
                    },
                    magnitude=vpo_growth,
                )

            # ---------------------------------------------
            # Growth with healthy velocity
            # ---------------------------------------------

            if (
                valid_number(units_growth)
                and valid_number(vpo_growth)
                and units_growth >= growth_threshold
                and vpo_growth >= 0
            ):
                add_signal(
                    signal_type="growth_with_velocity",
                    direction="positive",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "units_l3m_pct":
                            units_growth,
                        "revenue_l3m_pct":
                            revenue_growth,
                        "buying_stores_l3m_pct":
                            store_growth,
                        "vpo_l3m_pct":
                            vpo_growth,
                    },
                    magnitude=max(
                        units_growth,
                        vpo_growth,
                    ),
                )

            # ---------------------------------------------
            # Growth with velocity pressure
            # ---------------------------------------------

            if (
                valid_number(units_growth)
                and valid_number(store_growth)
                and valid_number(vpo_growth)
                and units_growth >= growth_threshold
                and store_growth >= distribution_threshold
                and vpo_growth <= -velocity_threshold
            ):
                add_signal(
                    signal_type="growth_with_velocity_pressure",
                    direction="neutral",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "units_l3m_pct":
                            units_growth,
                        "revenue_l3m_pct":
                            revenue_growth,
                        "buying_stores_l3m_pct":
                            store_growth,
                        "vpo_l3m_pct":
                            vpo_growth,
                    },
                    magnitude=max(
                        units_growth,
                        store_growth,
                        abs(vpo_growth),
                    ),
                )

    # -----------------------------------------------------
    # 2. Relative velocity comparisons
    # -----------------------------------------------------

    overall_vpo = None

    if (
        overall_df is not None
        and not overall_df.empty
        and "vpo_3m" in overall_df.columns
        and pd.notna(overall_df.iloc[0]["vpo_3m"])
    ):
        overall_vpo = overall_df.iloc[0]["vpo_3m"]

    # SKU-level benchmark lookup
    sku_df = analysis.get("sku")

    sku_vpo_lookup = {}

    if (
        sku_df is not None
        and not sku_df.empty
    ):
        sku_vpo_lookup = (
            sku_df
            .dropna(
                subset=[
                    "sku",
                    "vpo_3m",
                ]
            )
            .set_index("sku")["vpo_3m"]
            .to_dict()
        )

    comparison_scopes = {
        "sku": "sku",
        "retailer": "retailer",
        "state": "state",
        "retailer_sku": "retailer_sku",
        "state_sku": "state_sku",
    }

    for analysis_key, scope_type in comparison_scopes.items():

        df = analysis.get(analysis_key)

        if df is None or df.empty:
            continue

        for _, row in df.iterrows():

            vpo = row.get(
                "vpo_3m"
            )

            buying_stores = row.get(
                "buying_stores_3m"
            )

            if not valid_number(vpo):
                continue

            if (
                valid_number(buying_stores)
                and buying_stores < min_buying_stores
            ):
                continue

            # ---------------------------------------------
            # SKU × retailer / state
            #
            # Compare against that SKU's overall velocity
            # ---------------------------------------------

            if scope_type in [
                "retailer_sku",
                "state_sku",
            ]:

                sku = row.get("sku")

                benchmark_vpo = (
                    sku_vpo_lookup.get(sku)
                )

                benchmark_type = "sku_overall"

            # ---------------------------------------------
            # Everything else compares to total business
            # ---------------------------------------------

            else:
                benchmark_vpo = overall_vpo
                benchmark_type = "business_overall"

            if (
                not valid_number(benchmark_vpo)
                or benchmark_vpo == 0
            ):
                continue

            difference_pct = (
                vpo / benchmark_vpo
            ) - 1

            # ---------------------------------------------
            # Outperformance
            # ---------------------------------------------

            if (
                difference_pct
                >= comparison_threshold
            ):
                add_signal(
                    signal_type="velocity_outperformance",
                    direction="positive",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "vpo_3m":
                            vpo,
                        "vpo_difference_pct":
                            difference_pct,
                    },
                    benchmark={
                        "type":
                            benchmark_type,
                        "vpo_3m":
                            benchmark_vpo,
                    },
                    magnitude=difference_pct,
                )

            # ---------------------------------------------
            # Underperformance
            # ---------------------------------------------

            elif (
                difference_pct
                <= -comparison_threshold
            ):
                add_signal(
                    signal_type="velocity_underperformance",
                    direction="negative",
                    scope_type=scope_type,
                    row=row,
                    metrics={
                        "vpo_3m":
                            vpo,
                        "vpo_difference_pct":
                            difference_pct,
                    },
                    benchmark={
                        "type":
                            benchmark_type,
                        "vpo_3m":
                            benchmark_vpo,
                    },
                    magnitude=difference_pct,
                )

    # -----------------------------------------------------
    # Rank strongest signals first
    # -----------------------------------------------------

    signals = sorted(
        signals,
        key=lambda x: x["strength"],
        reverse=True,
    )

    return signals


def build_business_stories(
    df: pd.DataFrame,
    df_full: pd.DataFrame,
    active_pods_df: pd.DataFrame,
    analysis: dict,
    signals: list[dict],
) -> list[dict]:
    """
    Combines raw signals + diagnostics into a smaller set
    of business stories.

    V1:
    - group signals by scope
    - summarize the strongest signals
    - run units growth decomposition where relevant
    - classify the story using both distribution and velocity
    - return structured stories
    """

    if not signals:
        return []

    stories = []

    # -----------------------------------------------------
    # Group signals by scope
    # -----------------------------------------------------

    grouped = {}

    for signal in signals:
        scope_type = signal.get("scope_type")
        scope = signal.get("scope", {})

        scope_key = (
            scope_type,
            tuple(sorted(scope.items())),
        )

        grouped.setdefault(scope_key, []).append(signal)

    # -----------------------------------------------------
    # Build one story per scope
    # -----------------------------------------------------

    for (scope_type, scope_items), scope_signals in grouped.items():

        scope = dict(scope_items)

        # ---------------------------------------------
        # Pull signal types / directions
        # ---------------------------------------------

        signal_types = [
            signal["signal_type"]
            for signal in scope_signals
        ]

        directions = [
            signal["direction"]
            for signal in scope_signals
        ]

        # ---------------------------------------------
        # Find strongest signal
        # ---------------------------------------------

        strongest_signal = max(
            scope_signals,
            key=lambda x: x.get("strength", 0),
        )

        # ---------------------------------------------
        # Build dataframe for this scope
        # ---------------------------------------------

        df_scope = df.copy()

        df_full_scope = df_full.copy()
        active_pods_scope = active_pods_df.copy()

        if "chain" in scope:
            df_scope = df_scope[df_scope["chain"] == scope["chain"]]
            df_full_scope = df_full_scope[df_full_scope["chain"] == scope["chain"]]
            active_pods_scope = active_pods_scope[
                active_pods_scope["chain"] == scope["chain"]
            ]

        if "state" in scope:
            df_scope = df_scope[df_scope["state"] == scope["state"]]
            df_full_scope = df_full_scope[df_full_scope["state"] == scope["state"]]
            active_pods_scope = active_pods_scope[
                active_pods_scope["state"] == scope["state"]
            ]

        if "sku" in scope:
            df_scope = df_scope[df_scope["sku"] == scope["sku"]]
            df_full_scope = df_full_scope[df_full_scope["sku"] == scope["sku"]]
            active_pods_scope = active_pods_scope[
                active_pods_scope["sku"] == scope["sku"]
            ]

        # ---------------------------------------------
        # Diagnostics
        # ---------------------------------------------

        diagnostics = {}

        has_unit_change_signal = any(
            signal_type in signal_types
            for signal_type in [
                "unit_growth",
                "unit_decline",
                "growth_with_velocity",
                "growth_with_velocity_pressure",
            ]
        )

        if has_unit_change_signal:

            group_cols = []

            if "chain" in scope:
                group_cols.append("chain")

            if "state" in scope:
                group_cols.append("state")

            if "sku" in scope:
                group_cols.append("sku")

            decomp = calculate_units_growth_decomposition(
                df=df_scope,
                df_full=df_full_scope,
                active_pods_df=active_pods_scope,
                group_cols=group_cols,
            )

            if decomp is not None and not decomp.empty:
                row = decomp.iloc[0]

                diagnostics["units_growth_driver"] = {
                    "total_change":
                        row.get("total_change"),

                    "distribution_impact":
                        row.get("distribution_impact"),

                    "velocity_impact":
                        row.get("velocity_impact"),

                    "distribution_share":
                        row.get("distribution_share"),

                    "velocity_share":
                        row.get("velocity_share"),

                    "primary_driver":
                        row.get("primary_driver"),
                }

        # ---------------------------------------------
        # Determine overall story direction
        # ---------------------------------------------

        has_positive = "positive" in directions
        has_negative = "negative" in directions

        if has_positive and not has_negative:
            direction = "positive"

        elif has_negative and not has_positive:
            direction = "negative"

        else:
            direction = "mixed"

        # ---------------------------------------------
        # Default story type
        # ---------------------------------------------

        story_type = strongest_signal["signal_type"]

        # ---------------------------------------------
        # Growth / decline classification
        # ---------------------------------------------

        growth_driver = diagnostics.get(
            "units_growth_driver"
        )

        if growth_driver:

            distribution_impact = growth_driver.get(
                "distribution_impact"
            )

            velocity_impact = growth_driver.get(
                "velocity_impact"
            )

            distribution_share = growth_driver.get(
                "distribution_share"
            )

            velocity_share = growth_driver.get(
                "velocity_share"
            )

            has_unit_growth = any(
                signal_type in signal_types
                for signal_type in [
                    "unit_growth",
                    "growth_with_velocity",
                    "growth_with_velocity_pressure",
                ]
            )

            has_unit_decline = (
                "unit_decline" in signal_types
            )

            # -----------------------------------------
            # UNIT GROWTH
            # -----------------------------------------

            if has_unit_growth:

                # Both distribution and velocity
                # contributed positively
                if (
                    distribution_impact is not None
                    and velocity_impact is not None
                    and distribution_impact > 0
                    and velocity_impact > 0
                ):

                    if (
                        distribution_share is not None
                        and velocity_share is not None
                        and abs(distribution_share) >= 0.75
                    ):
                        story_type = (
                            "distribution_led_growth_with_velocity"
                        )

                    elif (
                        distribution_share is not None
                        and velocity_share is not None
                        and abs(velocity_share) >= 0.75
                    ):
                        story_type = (
                            "velocity_led_growth_with_distribution"
                        )

                    else:
                        story_type = (
                            "distribution_and_velocity_growth"
                        )

                # Distribution positive,
                # velocity negative
                elif (
                    distribution_impact is not None
                    and velocity_impact is not None
                    and distribution_impact > 0
                    and velocity_impact < 0
                ):
                    story_type = (
                        "distribution_growth_offset_by_velocity_pressure"
                    )

                # Velocity positive,
                # distribution negative
                elif (
                    distribution_impact is not None
                    and velocity_impact is not None
                    and distribution_impact < 0
                    and velocity_impact > 0
                ):
                    story_type = (
                        "velocity_growth_offset_by_distribution"
                    )

                # Distribution positive,
                # velocity flat / unavailable
                elif (
                    distribution_impact is not None
                    and distribution_impact > 0
                ):
                    story_type = (
                        "distribution_led_growth"
                    )

                # Velocity positive,
                # distribution flat / unavailable
                elif (
                    velocity_impact is not None
                    and velocity_impact > 0
                ):
                    story_type = (
                        "velocity_led_growth"
                    )

            # -----------------------------------------
            # UNIT DECLINE
            # -----------------------------------------

            elif has_unit_decline:

                # Both distribution and velocity
                # contributed negatively
                if (
                    distribution_impact is not None
                    and velocity_impact is not None
                    and distribution_impact < 0
                    and velocity_impact < 0
                ):

                    if (
                        distribution_share is not None
                        and velocity_share is not None
                        and abs(distribution_share) >= 0.75
                    ):
                        story_type = (
                            "distribution_led_decline_with_velocity_pressure"
                        )

                    elif (
                        distribution_share is not None
                        and velocity_share is not None
                        and abs(velocity_share) >= 0.75
                    ):
                        story_type = (
                            "velocity_led_decline_with_distribution_loss"
                        )

                    else:
                        story_type = (
                            "distribution_and_velocity_decline"
                        )

                # Distribution down,
                # velocity helping
                elif (
                    distribution_impact is not None
                    and velocity_impact is not None
                    and distribution_impact < 0
                    and velocity_impact > 0
                ):
                    story_type = (
                        "distribution_decline_offset_by_velocity_growth"
                    )

                # Velocity down,
                # distribution helping
                elif (
                    distribution_impact is not None
                    and velocity_impact is not None
                    and distribution_impact > 0
                    and velocity_impact < 0
                ):
                    story_type = (
                        "velocity_decline_offset_by_distribution_growth"
                    )

                elif (
                    distribution_impact is not None
                    and distribution_impact < 0
                ):
                    story_type = (
                        "distribution_led_decline"
                    )

                elif (
                    velocity_impact is not None
                    and velocity_impact < 0
                ):
                    story_type = (
                        "velocity_led_decline"
                    )

        # ---------------------------------------------
        # Story strength
        # ---------------------------------------------

        strength = max(
            signal.get("strength", 0)
            for signal in scope_signals
        )

        # ---------------------------------------------
        # Build structured story
        # ---------------------------------------------

        stories.append(
            {
                "story_type": story_type,
                "direction": direction,

                "scope_type": scope_type,
                "scope": scope,

                "signal_types": signal_types,

                "diagnostics": diagnostics,

                "evidence": {
                    signal["signal_type"]: signal.get(
                        "metrics",
                        {},
                    )
                    for signal in scope_signals
                },

                "strength": strength,
            }
        )

    # -----------------------------------------------------
    # Strongest stories first
    # -----------------------------------------------------

    stories = sorted(
        stories,
        key=lambda x: x["strength"],
        reverse=True,
    )

    return stories

def organize_business_stories(
    stories: list[dict],
) -> dict:
    """
    Organizes diagnosed business stories into the four
    user-facing views of the business.

    Cross-cut stories such as retailer_sku and state_sku
    are treated as supporting evidence, not standalone sections.
    """

    organized = {
        "overall": [],
        "sku": [],
        "retailer": [],
        "state": [],
    }

    if not stories:
        return organized

    # -----------------------------------------------------
    # Split primary vs supporting stories
    # -----------------------------------------------------

    overall_stories = [
        story
        for story in stories
        if story.get("scope_type") == "business"
    ]

    sku_stories = [
        story
        for story in stories
        if story.get("scope_type") == "sku"
    ]

    retailer_stories = [
        story
        for story in stories
        if story.get("scope_type") == "retailer"
    ]

    state_stories = [
        story
        for story in stories
        if story.get("scope_type") == "state"
    ]

    retailer_sku_stories = [
        story
        for story in stories
        if story.get("scope_type") == "retailer_sku"
    ]

    state_sku_stories = [
        story
        for story in stories
        if story.get("scope_type") == "state_sku"
    ]

    # -----------------------------------------------------
    # Overall
    # -----------------------------------------------------

    organized["overall"] = sorted(
        overall_stories,
        key=lambda x: x.get("strength", 0),
        reverse=True,
    )[:1]

    # -----------------------------------------------------
    # SKU stories
    #
    # Attach retailer/state detail for each SKU
    # -----------------------------------------------------

    for story in sku_stories:

        sku = story.get("scope", {}).get("sku")

        supporting = [
            child
            for child in retailer_sku_stories + state_sku_stories
            if child.get("scope", {}).get("sku") == sku
        ]

        story = story.copy()

        story["supporting_stories"] = sorted(
            supporting,
            key=lambda x: x.get("strength", 0),
            reverse=True,
        )

        organized["sku"].append(story)

    # -----------------------------------------------------
    # Retailer stories
    #
    # Attach SKU detail within each retailer
    # -----------------------------------------------------

    for story in retailer_stories:

        chain = story.get("scope", {}).get("chain")

        supporting = [
            child
            for child in retailer_sku_stories
            if child.get("scope", {}).get("chain") == chain
        ]

        story = story.copy()

        story["supporting_stories"] = sorted(
            supporting,
            key=lambda x: x.get("strength", 0),
            reverse=True,
        )

        organized["retailer"].append(story)

    # -----------------------------------------------------
    # State stories
    #
    # Attach SKU detail within each state
    # -----------------------------------------------------

    for story in state_stories:

        state = story.get("scope", {}).get("state")

        supporting = [
            child
            for child in state_sku_stories
            if child.get("scope", {}).get("state") == state
        ]

        story = story.copy()

        story["supporting_stories"] = sorted(
            supporting,
            key=lambda x: x.get("strength", 0),
            reverse=True,
        )

        organized["state"].append(story)

    # -----------------------------------------------------
    # Rank primary stories within each section
    # -----------------------------------------------------

    for key in [
        "sku",
        "retailer",
        "state",
    ]:
        organized[key] = sorted(
            organized[key],
            key=lambda x: x.get("strength", 0),
            reverse=True,
        )

    return organized

def build_business_synthesis(
    organized_stories: dict,
    top_n_drivers: int = 3,
    top_n_divergences: int = 2,
) -> dict:
    """
    Reads already-diagnosed business stories and synthesizes them into:

    1. Overall distribution / velocity pattern
    2. Biggest distribution drivers
    3. Biggest velocity drivers
    4. Meaningful upside divergences
    5. Meaningful downside divergences

    This function does not recalculate business metrics.
    """

    result = {
        "overall": None,
        "distribution_drivers": {
            "retailer": [],
            "sku": [],
            "state": [],
        },
        "velocity_drivers": {
            "retailer": [],
            "sku": [],
            "state": [],
        },
        "upside_divergences": [],
        "downside_divergences": [],
    }

    if not organized_stories:
        return result

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def get_driver(story: dict) -> dict:
        return story.get("diagnostics", {}).get("units_growth_driver", {})

    def get_direction(value):
        if value is None:
            return 0
        if value > 0:
            return 1
        if value < 0:
            return -1
        return 0

    def get_pattern(story: dict):
        driver = get_driver(story)

        distribution_impact = driver.get("distribution_impact")
        velocity_impact = driver.get("velocity_impact")

        if distribution_impact is None and velocity_impact is None:
            return None

        return (
            get_direction(distribution_impact),
            get_direction(velocity_impact),
        )

    def simplify_story(story: dict) -> dict:
        driver = get_driver(story)

        return {
            "scope_type": story.get("scope_type"),
            "scope": story.get("scope", {}),
            "story_type": story.get("story_type"),
            "direction": story.get("direction"),
            "pattern": get_pattern(story),
            "distribution_impact": driver.get("distribution_impact"),
            "velocity_impact": driver.get("velocity_impact"),
            "total_change": driver.get("total_change"),
            "strength": story.get("strength", 0),
        }

    # -----------------------------------------------------
    # 1. Overall pattern
    # -----------------------------------------------------

    overall_stories = organized_stories.get("overall", [])

    if not overall_stories:
        return result

    overall_story = overall_stories[0]
    overall_driver = get_driver(overall_story)
    overall_pattern = get_pattern(overall_story)

    if overall_pattern is None:
        return result

    overall_distribution_direction = overall_pattern[0]
    overall_velocity_direction = overall_pattern[1]

    result["overall"] = {
        "story_type": overall_story.get("story_type"),
        "direction": overall_story.get("direction"),
        "pattern": overall_pattern,
        "total_change": overall_driver.get("total_change"),
        "distribution_impact": overall_driver.get("distribution_impact"),
        "velocity_impact": overall_driver.get("velocity_impact"),
        "distribution_share": overall_driver.get("distribution_share"),
        "velocity_share": overall_driver.get("velocity_share"),
        "primary_driver": overall_driver.get("primary_driver"),
        "strength": overall_story.get("strength", 0),
    }

    # -----------------------------------------------------
    # 2. Child stories
    # -----------------------------------------------------

    scope_map = {
        "retailer": organized_stories.get("retailer", []),
        "sku": organized_stories.get("sku", []),
        "state": organized_stories.get("state", []),
    }

    # -----------------------------------------------------
    # 3. Distribution drivers
    # -----------------------------------------------------

    for scope_type, stories in scope_map.items():
        candidates = []

        for story in stories:
            pattern = get_pattern(story)

            if pattern is None:
                continue

            if pattern[0] != overall_distribution_direction:
                continue

            distribution_impact = get_driver(story).get("distribution_impact")

            if distribution_impact is None:
                continue

            candidates.append(story)

        candidates = sorted(
            candidates,
            key=lambda story: abs(
                get_driver(story).get("distribution_impact") or 0
            ),
            reverse=True,
        )

        result["distribution_drivers"][scope_type] = [
            simplify_story(story)
            for story in candidates[:top_n_drivers]
        ]

    # -----------------------------------------------------
    # 4. Velocity drivers
    # -----------------------------------------------------

    for scope_type, stories in scope_map.items():
        candidates = []

        for story in stories:
            pattern = get_pattern(story)

            if pattern is None:
                continue

            if pattern[1] != overall_velocity_direction:
                continue

            velocity_impact = get_driver(story).get("velocity_impact")

            if velocity_impact is None:
                continue

            candidates.append(story)

        candidates = sorted(
            candidates,
            key=lambda story: abs(
                get_driver(story).get("velocity_impact") or 0
            ),
            reverse=True,
        )

        result["velocity_drivers"][scope_type] = [
            simplify_story(story)
            for story in candidates[:top_n_drivers]
        ]

    # -----------------------------------------------------
    # 5. Divergences
    # -----------------------------------------------------

    upside_divergences = []
    downside_divergences = []

    for scope_type, stories in scope_map.items():
        for story in stories:
            child_pattern = get_pattern(story)

            if child_pattern is None:
                continue

            child_distribution_direction = child_pattern[0]
            child_velocity_direction = child_pattern[1]

            # Same as overall = not a divergence
            if (
                child_distribution_direction == overall_distribution_direction
                and child_velocity_direction == overall_velocity_direction
            ):
                continue

            distribution_difference = (
                child_distribution_direction - overall_distribution_direction
            )
            velocity_difference = (
                child_velocity_direction - overall_velocity_direction
            )

            # Better or equal on both dimensions,
            # and strictly better on at least one.
            if (
                distribution_difference >= 0
                and velocity_difference >= 0
                and (distribution_difference > 0 or velocity_difference > 0)
            ):
                upside_divergences.append(story)

            # Worse or equal on both dimensions,
            # and strictly worse on at least one.
            elif (
                distribution_difference <= 0
                and velocity_difference <= 0
                and (distribution_difference < 0 or velocity_difference < 0)
            ):
                downside_divergences.append(story)

    # -----------------------------------------------------
    # 6. Rank divergences
    # -----------------------------------------------------

    upside_divergences = sorted(
        upside_divergences,
        key=lambda story: story.get("strength", 0),
        reverse=True,
    )

    downside_divergences = sorted(
        downside_divergences,
        key=lambda story: story.get("strength", 0),
        reverse=True,
    )

    result["upside_divergences"] = [
        simplify_story(story)
        for story in upside_divergences[:top_n_divergences]
    ]

    result["downside_divergences"] = [
        simplify_story(story)
        for story in downside_divergences[:top_n_divergences]
    ]

    return result

def build_business_narrative(synthesis: dict) -> dict:
    """
    Converts structured business synthesis into user-facing narrative.

    This function does NOT determine drivers, divergences, or context relevance.
    It only describes what the synthesis layer has already determined.
    """

    overall = synthesis.get("overall")

    if not overall:
        return {}

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def format_units(value):
        if value is None:
            return None

        sign = "+" if value > 0 else ""
        value = abs(value)

        if value >= 1000:
            formatted = f"{value / 1000:.1f}K"
        else:
            formatted = f"{value:,.0f}"

        return f"{sign}{formatted}" if sign else f"-{formatted}"

    def get_scope_label(item):
        scope = item.get("scope", {})
        return scope.get("chain") or scope.get("sku") or scope.get("state") or "Overall Business"

    def describe_overall(story_type):
        labels = {
            "distribution_and_velocity_growth":
                "The business is growing through both expanding distribution and stronger velocity.",

            "distribution_led_growth_with_velocity":
                "The business is growing primarily through distribution expansion, with velocity also contributing.",

            "velocity_led_growth_with_distribution":
                "The business is growing primarily through stronger velocity, with distribution also contributing.",

            "distribution_growth_offset_by_velocity_pressure":
                "The business is growing through distribution expansion despite softer velocity.",

            "velocity_growth_offset_by_distribution":
                "Stronger velocity is driving growth despite distribution pressure.",

            "distribution_led_growth":
                "The business is growing primarily through distribution expansion.",

            "velocity_led_growth":
                "The business is growing primarily through stronger velocity.",

            "distribution_and_velocity_decline":
                "The business is declining as both distribution and velocity weaken.",

            "distribution_led_decline_with_velocity_pressure":
                "The business is declining primarily from distribution losses, with weaker velocity adding pressure.",

            "velocity_led_decline_with_distribution_loss":
                "The business is declining primarily from weaker velocity, with distribution losses adding pressure.",

            "distribution_decline_offset_by_velocity_growth":
                "Distribution losses are driving the decline despite improving velocity.",

            "velocity_decline_offset_by_distribution_growth":
                "Velocity pressure is driving the decline despite expanding distribution.",

            "distribution_led_decline":
                "The business is declining primarily because of distribution losses.",

            "velocity_led_decline":
                "The business is declining primarily because of weaker velocity.",
        }

        return labels.get(story_type, "The business is showing a meaningful change in performance.")

    def build_driver_items(drivers, impact_key):
        items = []

        for scope_type in ["retailer", "sku", "state"]:
            for driver in drivers.get(scope_type, []):
                item = {
                    "scope_type": scope_type,
                    "label": get_scope_label(driver),
                    "impact": driver.get(impact_key),
                    "impact_display": format_units(driver.get(impact_key)),
                }

                # Context may be attached by synthesis later.
                if driver.get("context"):
                    item["context"] = driver["context"]

                items.append(item)

        return items

    def build_divergence_items(divergences):
        items = []

        for divergence in divergences:
            item = {
                "scope_type": divergence.get("scope_type"),
                "label": get_scope_label(divergence),
                "story_type": divergence.get("story_type"),
                "distribution_impact": divergence.get("distribution_impact"),
                "velocity_impact": divergence.get("velocity_impact"),
                "total_change": divergence.get("total_change"),
            }

            if divergence.get("context"):
                item["context"] = divergence["context"]

            items.append(item)

        return items

    # -----------------------------------------------------
    # Primary story
    # -----------------------------------------------------

    headline = describe_overall(overall.get("story_type"))

    total_change = overall.get("total_change")
    distribution_impact = overall.get("distribution_impact")
    velocity_impact = overall.get("velocity_impact")

    total_display = format_units(total_change)
    distribution_display = format_units(distribution_impact)
    velocity_display = format_units(velocity_impact)

    summary = (
        f"Units changed by {total_display}, with distribution contributing "
        f"{distribution_display} units and velocity contributing {velocity_display} units."
    )

    # -----------------------------------------------------
    # Supporting sections
    # -----------------------------------------------------

    distribution_drivers = build_driver_items(
        synthesis.get("distribution_drivers", {}),
        "distribution_impact",
    )

    velocity_drivers = build_driver_items(
        synthesis.get("velocity_drivers", {}),
        "velocity_impact",
    )

    upside_divergences = build_divergence_items(
        synthesis.get("upside_divergences", [])
    )

    downside_divergences = build_divergence_items(
        synthesis.get("downside_divergences", [])
    )

    # -----------------------------------------------------
    # Narrative
    # -----------------------------------------------------

    return {
        "headline": headline,
        "summary": summary,

        "evidence": {
            "total_change": total_change,
            "total_change_display": total_display,
            "distribution_impact": distribution_impact,
            "distribution_impact_display": distribution_display,
            "velocity_impact": velocity_impact,
            "velocity_impact_display": velocity_display,
        },

        "sections": [
            {
                "type": "distribution_drivers",
                "title": "What's driving distribution",
                "items": distribution_drivers,
            },
            {
                "type": "velocity_drivers",
                "title": "What's driving velocity",
                "items": velocity_drivers,
            },
            {
                "type": "upside_divergences",
                "title": "Where the pattern is stronger",
                "items": upside_divergences,
            },
            {
                "type": "downside_divergences",
                "title": "Where the pattern is weaker",
                "items": downside_divergences,
            },
        ],

        "context": synthesis.get("context", []),
    }
