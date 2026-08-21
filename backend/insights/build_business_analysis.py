import pandas as pd

from backend.insights.insights_helper import _build_3m_metrics
from backend.insights.diagnostics import (
    calculate_units_growth_decomposition_3m,
)


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



import pandas as pd

from backend.insights.diagnostics import (
    calculate_units_growth_decomposition_3m,
)


def build_business_stories(
    df: pd.DataFrame,
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

        if "chain" in scope:
            df_scope = df_scope[
                df_scope["chain"] == scope["chain"]
            ]

        if "state" in scope:
            df_scope = df_scope[
                df_scope["state"] == scope["state"]
            ]

        if "sku" in scope:
            df_scope = df_scope[
                df_scope["sku"] == scope["sku"]
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

            decomp = calculate_units_growth_decomposition_3m(
                df_filtered=df_scope,
                df_full=df_scope,
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