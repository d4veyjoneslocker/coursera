import math
import time
import pandas as pd

from backend.metrics.metric_calculators import calculate_vpo, _calculate_store_vpo_fast


def compose_business_review(
    review,
    narrative_tree,
    df,
    current_period,
    prior_period,
    within_period=None,
    top_n=10,
):
    """
    Build the single frontend-ready Business Review payload.

    `within_period` is optional and should be the raw analytical result from the
    second review run, e.g. Q2 vs Q1 for H1.
    """

    total_start = time.perf_counter()

    current_start = pd.Period(current_period["start"], freq="M")
    current_end = pd.Period(current_period["end"], freq="M")
    prior_start = pd.Period(prior_period["start"], freq="M")
    prior_end = pd.Period(prior_period["end"], freq="M")

    timings = {}

    # ------------------------------------------------------------------
    # Scorecard
    # ------------------------------------------------------------------
    t = time.perf_counter()

    scorecard = _build_scorecard(review.get("business", {}))

    timings["scorecard"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Growth decomposition
    # ------------------------------------------------------------------
    t = time.perf_counter()

    growth_decomposition = _build_growth_decomposition(narrative_tree)

    timings["growth_decomposition"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Stories
    # ------------------------------------------------------------------
    t = time.perf_counter()

    stories = _build_review_stories(narrative_tree)

    timings["stories"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Retailers
    # ------------------------------------------------------------------
    t = time.perf_counter()

    retailers = _build_entity_summary(
        review.get("chains", {}),
        entity_key="chain",
        top_n=top_n,
    )

    timings["retailers"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    t = time.perf_counter()

    products = _build_entity_summary(
        review.get("skus", {}),
        entity_key="sku",
        top_n=top_n,
    )

    timings["products"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Stores
    # ------------------------------------------------------------------
    t = time.perf_counter()

    stores = _build_store_summary(
        df=df,
        current_start=current_start,
        current_end=current_end,
        prior_start=prior_start,
        prior_end=prior_end,
        top_n=top_n,
    )

    timings["stores"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Distribution
    # ------------------------------------------------------------------
    t = time.perf_counter()

    distribution = _build_distribution_summary(
        df=df,
        current_start=current_start,
        current_end=current_end,
    )

    timings["distribution"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Hero
    # ------------------------------------------------------------------
    t = time.perf_counter()

    hero = _build_hero(
        scorecard=scorecard,
        growth_decomposition=growth_decomposition,
        stories=stories,
    )

    timings["hero"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Inside-period review
    # ------------------------------------------------------------------
    t = time.perf_counter()

    inside_period = _build_inside_period(
        within_period=within_period,
        df=df,
        top_n=top_n,
    )

    timings["inside_period"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Key stories
    # ------------------------------------------------------------------
    t = time.perf_counter()

    key_stories = _build_key_stories(
        growth_decomposition=growth_decomposition,
        stories=stories,
        inside_period=inside_period,
    )

    timings["key_stories"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Build final payload
    # ------------------------------------------------------------------
    t = time.perf_counter()

    payload = {
        "meta": {
            "period": _serialize_period(current_period),
            "comparison": _serialize_period(prior_period),
        },
        "hero": hero,
        "scorecard": scorecard,
        "key_stories": key_stories,
        "inside_period": inside_period,
        "retailers": {
            **retailers,
            "visuals": _build_ranking_visuals(
                rows=retailers.get("top", []),
                entity_key="chain",
                title="Top retailers by units",
            ),
        },
        "products": {
            **products,
            "visuals": _build_ranking_visuals(
                rows=products.get("top", []),
                entity_key="sku",
                title="Top products by units",
            ),
        },
        "stores": {
            **stores,
            "visuals": _build_store_visuals(stores),
        },
        "distribution": {
            "summary": distribution,
            "visuals": [],
        },
        "additional_stories": _build_additional_stories(stories),
    }

    timings["payload_build"] = time.perf_counter() - t
    timings["total"] = time.perf_counter() - total_start

    print("\n===== BUSINESS REVIEW COMPOSE TIMINGS =====")
    for name, seconds in timings.items():
        print(f"{name:25s}: {seconds:.3f}s")
    print("===========================================\n")

    return payload


# ---------------------------------------------------------------------------
# CORE SECTIONS
# ---------------------------------------------------------------------------

def _build_scorecard(business_metrics):
    order = [
        ("units", "Units"),
        ("buying_stores", "Buying stores"),
        ("active_pods", "Active PODs"),
        ("velocity", "Velocity"),
        ("reorder_rate", "Reorder rate"),
    ]

    rows = []

    for metric, label in order:
        values = business_metrics.get(metric)
        if not isinstance(values, dict):
            continue

        rows.append({
            "metric": metric,
            "label": label,
            "current": _safe_optional_number(values.get("current")),
            "comparison": _safe_optional_number(values.get("comparison")),
            "abs_change": _safe_optional_number(values.get("abs_change")),
            "pct_change": _safe_optional_number(values.get("pct_change")),
        })

    return rows


def _build_hero(scorecard, growth_decomposition, stories):
    units = _find_scorecard_metric(scorecard, "units")
    buying_stores = _find_scorecard_metric(scorecard, "buying_stores")

    positive_drivers = [
        item for item in growth_decomposition
        if _safe_number(item.get("impact")) > 0
    ]
    positive_drivers.sort(
        key=lambda item: _safe_number(item.get("impact")),
        reverse=True,
    )
    primary_driver = positive_drivers[0] if positive_drivers else None

    headline = primary_driver.get("headline") if primary_driver else None

    summary_parts = []
    if units:
        current = units.get("current")
        change = units.get("abs_change")
        if current is not None and change is not None:
            summary_parts.append(
                f"Volume reached {round(current):,} units, "
                f"up {round(change):,} versus the comparison period."
            )

    if primary_driver and primary_driver.get("share_of_change") is not None:
        share = primary_driver["share_of_change"]
        if share > 0:
            summary_parts.append(
                f"{share:.0%} of the change came from "
                f"{_display_driver(primary_driver.get('driver')).lower()}."
            )

    highlight = None
    if buying_stores:
        highlight = {
            "metric": "buying_stores",
            "label": "Buying stores",
            "current": buying_stores.get("current"),
            "comparison": buying_stores.get("comparison"),
            "abs_change": buying_stores.get("abs_change"),
            "pct_change": buying_stores.get("pct_change"),
        }

    return {
        "headline": headline,
        "summary": " ".join(summary_parts) if summary_parts else None,
        "highlight": highlight,
    }


def _build_key_stories(
    growth_decomposition,
    stories,
    inside_period=None,
    max_stories=3,
):
    """
    Build the executive 'What mattered' section.

    Priority:
      1. Biggest full-period positive driver
      2. Full-period headwind / decline, if one exists
      3. Broad within-period momentum
      4. Strongest scoped within-period retailer / SKU story

    This keeps the section concise while allowing an expansion-heavy
    half/year to gain useful texture from the quarter-vs-quarter analysis.
    """

    selected = []

    # ------------------------------------------------------------------
    # 1. Biggest full-period positive driver
    # ------------------------------------------------------------------
    positive_drivers = [
        item
        for item in growth_decomposition
        if _safe_number(item.get("impact")) > 0
    ]

    primary_driver = (
        max(
            positive_drivers,
            key=lambda item: _safe_number(item.get("impact")),
        )
        if positive_drivers
        else None
    )

    if primary_driver:
        selected.append({
            "type": "growth_driver",
            "headline": primary_driver.get("headline"),
            "detail": primary_driver.get("detail"),
            "impact": primary_driver.get("impact"),
            "driver_type": primary_driver.get("driver"),
        })

    # ------------------------------------------------------------------
    # 2. Full-period headwind, if one exists
    # ------------------------------------------------------------------
    headwind = next(
        (
            story
            for story in stories
            if story.get("type") in {"headwind", "decline"}
        ),
        None,
    )

    if headwind and len(selected) < max_stories:
        _append_story_if_new(selected, headwind)

    # ------------------------------------------------------------------
    # 3. Broad within-period momentum
    # ------------------------------------------------------------------
    if inside_period and len(selected) < max_stories:
        momentum_headline = inside_period.get("headline")
        momentum_summary = inside_period.get("summary")

        if momentum_headline:
            _append_story_if_new(
                selected,
                {
                    "type": "momentum",
                    "headline": momentum_headline,
                    "detail": momentum_summary,
                    "impact": _inside_period_unit_change(inside_period),
                    "driver_type": "inside_period",
                },
            )

    # ------------------------------------------------------------------
    # 4. Strongest useful scoped within-period story
    # ------------------------------------------------------------------
    if inside_period and len(selected) < max_stories:
        within_stories = inside_period.get("stories") or []

        scoped_story = next(
            (
                story
                for story in within_stories
                if _is_useful_scoped_story(story)
                and not _story_already_selected(selected, story)
            ),
            None,
        )

        if scoped_story:
            _append_story_if_new(selected, scoped_story)

    # ------------------------------------------------------------------
    # Visuals
    # ------------------------------------------------------------------
    visuals = []

    if growth_decomposition:
        visuals.append({
            "type": "stacked_share_bar",
            "title": "What drove unit change",
            "metric": "units",
            "data": [
                {
                    "label": _display_driver(item.get("driver")),
                    "value": item.get("impact"),
                    "share": item.get("share_of_change"),
                }
                for item in growth_decomposition
            ],
        })

    return {
        "stories": selected[:max_stories],
        "visuals": visuals,
    }


def _append_story_if_new(selected, story):
    if not story or not story.get("headline"):
        return

    if _story_already_selected(selected, story):
        return

    selected.append({
        key: value
        for key, value in story.items()
        if not key.startswith("_")
    })


def _story_already_selected(selected, candidate):
    candidate_headline = _normalize_headline(
        candidate.get("headline")
    )

    if not candidate_headline:
        return False

    return any(
        _normalize_headline(story.get("headline")) == candidate_headline
        for story in selected
    )


def _normalize_headline(value):
    if not value:
        return ""

    return " ".join(
        str(value)
        .lower()
        .strip()
        .split()
    )


def _inside_period_unit_change(inside_period):
    scorecard = inside_period.get("scorecard") or []

    units = next(
        (
            row
            for row in scorecard
            if row.get("metric") == "units"
        ),
        None,
    )

    if not units:
        return None

    return units.get("abs_change")


def _is_useful_scoped_story(story):
    """
    Prefer a retailer / SKU story that adds specificity to the broad
    within-period momentum story.
    """
    if not story or not story.get("headline"):
        return False

    scope = story.get("scope") or {}

    has_entity = bool(
        scope.get("chain")
        or scope.get("sku")
    )

    if not has_entity:
        return False

    return story.get("type") in {
        "growth_driver",
        "bright_spot",
        "headwind",
        "decline",
    }


def _build_inside_period(within_period, df, top_n=10):
    if not within_period:
        return None

    review = within_period.get("review") or {}
    narrative_tree = within_period.get("narrative_tree") or []
    current_period = within_period.get("current_period") or {}
    prior_period = within_period.get("prior_period") or {}

    if not current_period or not prior_period:
        return None

    scorecard = _build_scorecard(review.get("business", {}))
    growth_decomposition = _build_growth_decomposition(narrative_tree)
    stories = _build_review_stories(narrative_tree)

    current_label = current_period.get("label")
    prior_label = prior_period.get("label")

    units = _find_scorecard_metric(scorecard, "units")
    primary_driver = _largest_positive_driver(growth_decomposition)

    headline = None
    summary = None

    if units and units.get("pct_change") is not None:
        pct_change = units["pct_change"]

        if pct_change >= 0.10:
            headline = f"Momentum accelerated into {current_label}."
        elif pct_change <= -0.10:
            headline = f"Momentum slowed in {current_label}."
        else:
            headline = f"Momentum was relatively stable in {current_label}."

        if units.get("current") is not None and units.get("comparison") is not None:
            summary = (
                f"{current_label} volume was {round(units['current']):,} units "
                f"versus {round(units['comparison']):,} in {prior_label}."
            )

            if primary_driver and primary_driver.get("share_of_change") is not None:
                summary += (
                    f" {_display_driver(primary_driver.get('driver'))} accounted for "
                    f"{primary_driver['share_of_change']:.0%} of the change."
                )

    visuals = []

    if units:
        visuals.append({
            "type": "bar_chart",
            "title": "Quarterly unit momentum",
            "metric": "units",
            "data": [
                {
                    "label": prior_label,
                    "value": units.get("comparison"),
                },
                {
                    "label": current_label,
                    "value": units.get("current"),
                },
            ],
        })

    if growth_decomposition:
        visuals.append({
            "type": "donut_chart",
            "title": f"What drove {current_label} growth",
            "metric": "units",
            "data": [
                {
                    "label": _display_driver(item.get("driver")),
                    "value": item.get("impact"),
                    "share": item.get("share_of_change"),
                }
                for item in growth_decomposition
                if _safe_number(item.get("impact")) > 0
            ],
        })

    launch_health = _build_launch_health(stories)

    if launch_health:
        reorder_rate = _extract_reorder_rate(launch_health)

        if reorder_rate is not None:
            visuals.append({
                "type": "progress_bar",
                "title": "Recent-launch health",
                "value": reorder_rate,
                "label": launch_health.get("headline"),
            })

    return {
        "meta": {
            "label": f"{current_label} vs {prior_label}",
            "current": _serialize_period(current_period),
            "comparison": _serialize_period(prior_period),
        },
        "headline": headline,
        "summary": summary,
        "scorecard": scorecard,
        "visuals": visuals,
        "launch_health": launch_health,
        "stories": stories[:5],
    }


# ---------------------------------------------------------------------------
# RANKINGS
# ---------------------------------------------------------------------------

def _build_entity_summary(metric_tables, entity_key, top_n=10):
    """
    Build retailer / SKU summaries ranked by units, but enrich every row
    with the other entity-level metrics already available in the review.

    Ranking buckets remain unit-based:
      - top
      - gainers
      - decliners
      - current_only
      - lost

    Enriched metrics:
      - units
      - buying_stores
      - active_pods
      - velocity
      - reorder_rate

    Store summaries are intentionally handled separately in
    `_build_store_summary`, where the dedicated fast store-level VPO helper
    is used.
    """

    metric_keys = [
        "units",
        "buying_stores",
        "active_pods",
        "velocity",
        "reorder_rate",
    ]

    empty = {
        "top": [],
        "gainers": [],
        "decliners": [],
        "current_only": [],
        "lost": [],
    }

    units = _to_dataframe(metric_tables.get("units"))

    if units.empty or entity_key not in units.columns:
        return empty

    merged = None

    for metric in metric_keys:
        metric_df = _to_dataframe(metric_tables.get(metric))

        if metric_df.empty or entity_key not in metric_df.columns:
            continue

        metric_df = metric_df.copy()

        numeric_cols = [
            "value_current",
            "value_comparison",
            "abs_change",
            "pct_change",
        ]

        for col in numeric_cols:
            if col in metric_df.columns:
                metric_df[col] = pd.to_numeric(
                    metric_df[col],
                    errors="coerce",
                )

        keep_cols = [
            entity_key,
            *[
                col
                for col in numeric_cols
                if col in metric_df.columns
            ],
        ]

        metric_df = metric_df[keep_cols].copy()

        metric_df = metric_df.rename(
            columns={
                "value_current": f"{metric}_current",
                "value_comparison": f"{metric}_comparison",
                "abs_change": f"{metric}_abs_change",
                "pct_change": f"{metric}_pct_change",
            }
        )

        if merged is None:
            merged = metric_df
        else:
            merged = merged.merge(
                metric_df,
                on=entity_key,
                how="outer",
            )

    if merged is None or merged.empty:
        return empty

    for col in [
        "units_current",
        "units_comparison",
        "units_abs_change",
        "units_pct_change",
    ]:
        if col not in merged.columns:
            merged[col] = None

    current_active = (
        merged["units_current"].notna()
        & (merged["units_current"] > 0)
    )

    comparison_active = (
        merged["units_comparison"].notna()
        & (merged["units_comparison"] > 0)
    )

    top = (
        merged[current_active]
        .sort_values("units_current", ascending=False)
        .head(top_n)
    )

    comparable = merged[
        current_active
        & comparison_active
    ].copy()

    gainers = (
        comparable[comparable["units_abs_change"] > 0]
        .sort_values("units_abs_change", ascending=False)
        .head(top_n)
    )

    decliners = (
        comparable[comparable["units_abs_change"] < 0]
        .sort_values("units_abs_change", ascending=True)
        .head(top_n)
    )

    current_only = (
        merged[
            current_active
            & ~comparison_active
        ]
        .sort_values("units_current", ascending=False)
        .head(top_n)
    )

    lost = (
        merged[
            ~current_active
            & comparison_active
        ]
        .sort_values("units_comparison", ascending=False)
        .head(top_n)
    )

    def serialize_rows(frame):
        rows = []

        for _, row in frame.iterrows():
            rows.append({
                entity_key: _clean_value(row.get(entity_key)),
                "units": _entity_metric_payload(row, "units"),
                "buying_stores": _entity_metric_payload(
                    row,
                    "buying_stores",
                ),
                "active_pods": _entity_metric_payload(
                    row,
                    "active_pods",
                ),
                "velocity": _entity_metric_payload(
                    row,
                    "velocity",
                ),
                "reorder_rate": _entity_metric_payload(
                    row,
                    "reorder_rate",
                ),
            })

        return rows

    return {
        "top": serialize_rows(top),
        "gainers": serialize_rows(gainers),
        "decliners": serialize_rows(decliners),
        "current_only": serialize_rows(current_only),
        "lost": serialize_rows(lost),
    }


def _entity_metric_payload(row, metric):
    return {
        "current": _clean_value(row.get(f"{metric}_current")),
        "comparison": _clean_value(row.get(f"{metric}_comparison")),
        "abs_change": _clean_value(row.get(f"{metric}_abs_change")),
        "pct_change": _clean_value(row.get(f"{metric}_pct_change")),
    }


def _build_store_summary(
    df,
    current_start,
    current_end,
    prior_start,
    prior_end,
    top_n=10,
):
    total_start = time.perf_counter()
    timings = {}

    empty = {
        "top": [],
        "gainers": [],
        "decliners": [],
        "current_only": [],
        "lost": [],
    }

    if (
        df is None
        or df.empty
        or "coded_customer" not in df.columns
        or "month_year" not in df.columns
    ):
        return empty

    # ------------------------------------------------------------------
    # Filter periods
    # ------------------------------------------------------------------
    t = time.perf_counter()

    current_df = df[
        (df["month_year"] >= current_start)
        & (df["month_year"] <= current_end)
    ].copy()

    prior_df = df[
        (df["month_year"] >= prior_start)
        & (df["month_year"] <= prior_end)
    ].copy()

    timings["filter_periods"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Group columns
    # ------------------------------------------------------------------
    group_cols = ["coded_customer"]

    for col in ["chain", "customer_name", "city", "state"]:
        if col in df.columns:
            group_cols.append(col)

    # ------------------------------------------------------------------
    # Units aggregation
    # ------------------------------------------------------------------
    t = time.perf_counter()

    current_units = _group_units(
        current_df,
        group_cols,
        "value_current",
    )

    prior_units = _group_units(
        prior_df,
        group_cols,
        "value_comparison",
    )

    timings["unit_groupbys"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------
    t = time.perf_counter()

    stores = current_units.merge(
        prior_units,
        on=group_cols,
        how="outer",
    )

    stores["was_current"] = stores["value_current"].notna()
    stores["was_comparison"] = stores["value_comparison"].notna()

    stores["value_current"] = stores["value_current"].fillna(0)
    stores["value_comparison"] = stores["value_comparison"].fillna(0)

    stores["abs_change"] = (
        stores["value_current"] - stores["value_comparison"]
    )

    timings["units_merge"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Percent change
    # ------------------------------------------------------------------
    t = time.perf_counter()

    stores["pct_change"] = stores.apply(
        lambda row: _pct_change(
            row["value_current"],
            row["value_comparison"],
        ),
        axis=1,
    )

    timings["pct_change"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Months
    # ------------------------------------------------------------------
    current_vpo = _calculate_store_vpo_fast(
        df_filtered=current_df,
        group_cols=group_cols,
        start_period=current_start,
        end_period=current_end,
        value_name="velocity_current",
    )

    prior_vpo = _calculate_store_vpo_fast(
        df_filtered=prior_df,
        group_cols=group_cols,
        start_period=prior_start,
        end_period=prior_end,
        value_name="velocity_comparison",
    )

    timings["prior_vpo"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Merge VPO
    # ------------------------------------------------------------------
    t = time.perf_counter()

    if not current_vpo.empty:
        stores = stores.merge(
            current_vpo,
            on=group_cols,
            how="left",
        )
    else:
        stores["velocity_current"] = None

    if not prior_vpo.empty:
        stores = stores.merge(
            prior_vpo,
            on=group_cols,
            how="left",
        )
    else:
        stores["velocity_comparison"] = None

    timings["vpo_merge"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Velocity change
    # ------------------------------------------------------------------
    t = time.perf_counter()

    stores["velocity_change"] = stores.apply(
        lambda row: _pct_change(
            row.get("velocity_current"),
            row.get("velocity_comparison"),
        ),
        axis=1,
    )

    timings["velocity_change"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Rankings
    # ------------------------------------------------------------------
    t = time.perf_counter()

    top = (
        stores[stores["value_current"] > 0]
        .sort_values("value_current", ascending=False)
        .head(top_n)
    )

    gainers = (
        stores[
            stores["was_current"]
            & stores["was_comparison"]
            & (stores["abs_change"] > 0)
        ]
        .sort_values("abs_change", ascending=False)
        .head(top_n)
    )

    decliners = (
        stores[
            stores["was_current"]
            & stores["was_comparison"]
            & (stores["abs_change"] < 0)
        ]
        .sort_values("abs_change", ascending=True)
        .head(top_n)
    )

    current_only = (
        stores[
            stores["was_current"]
            & ~stores["was_comparison"]
            & (stores["value_current"] > 0)
        ]
        .sort_values("value_current", ascending=False)
        .head(top_n)
    )

    lost = (
        stores[
            ~stores["was_current"]
            & stores["was_comparison"]
            & (stores["value_comparison"] > 0)
        ]
        .sort_values("value_comparison", ascending=False)
        .head(top_n)
    )

    timings["rankings"] = time.perf_counter() - t

    # ------------------------------------------------------------------
    # Cleanup / serialization
    # ------------------------------------------------------------------
    t = time.perf_counter()

    for frame in [top, gainers, decliners, current_only, lost]:
        frame.drop(
            columns=["was_current", "was_comparison"],
            inplace=True,
            errors="ignore",
        )

    result = {
        "top": _records(top),
        "gainers": _records(gainers),
        "decliners": _records(decliners),
        "current_only": _records(current_only),
        "lost": _records(lost),
    }

    timings["serialization"] = time.perf_counter() - t
    timings["total"] = time.perf_counter() - total_start

    print("\n----- STORE SUMMARY TIMINGS -----")
    print(f"input rows              : {len(df):,}")
    print(f"current rows            : {len(current_df):,}")
    print(f"comparison rows         : {len(prior_df):,}")
    print(f"store result rows       : {len(stores):,}")

    for name, seconds in timings.items():
        print(f"{name:24s}: {seconds:.3f}s")

    print("---------------------------------\n")

    return result


# ---------------------------------------------------------------------------
# VISUAL SPECS
# ---------------------------------------------------------------------------

def _build_ranking_visuals(rows, entity_key, title):
    if not rows:
        return []

    data = [
        {
            "label": row.get(entity_key),
            "value": (row.get("units") or {}).get("current"),
        }
        for row in rows
        if (row.get("units") or {}).get("current") is not None
    ]

    if not data:
        return []

    return [{
        "type": "horizontal_bar_chart",
        "title": title,
        "metric": "units",
        "data": data,
    }]


def _build_store_visuals(stores):
    rows = stores.get("top", [])

    if not rows:
        return []

    return [{
        "type": "horizontal_bar_chart",
        "title": "Top stores by units",
        "metric": "units",
        "data": [
            {
                "label": _store_label(row),
                "value": row.get("value_current"),
                "velocity": row.get("velocity_current"),
            }
            for row in rows
        ],
    }]


# ---------------------------------------------------------------------------
# STORIES
# ---------------------------------------------------------------------------

def _build_growth_decomposition(narrative_tree):
    drivers = _get_driver_nodes(narrative_tree)
    total_impact = sum(
        _safe_number(node.get("impact"))
        for node in drivers
    )

    return [
        {
            "driver": node.get("driver_type"),
            "impact": _safe_number(node.get("impact")),
            "share_of_change": (
                _safe_number(node.get("impact")) / total_impact
                if total_impact
                else None
            ),
            "headline": node.get("headline"),
            "detail": node.get("detail"),
        }
        for node in drivers
    ]


def _build_review_stories(narrative_tree, max_per_type=5):
    nodes = [
        node
        for node in _flatten_tree(narrative_tree)
        if node.get("node_type") != "root"
        and node.get("headline")
    ]

    stories = []

    for node in nodes:
        story_type = _classify_review_story(node)

        if story_type is None:
            continue

        stories.append({
            "type": story_type,
            "headline": node.get("headline"),
            "detail": node.get("detail"),
            "impact": _safe_number(node.get("impact")),
            "scope": node.get("scope") or {},
            "driver_type": node.get("driver_type"),
            "metrics": node.get("metrics") or {},
            "classification": node.get("classification") or {},
            "surfaced_by": node.get("surfaced_by"),
            "_depth": node.get("_depth", 0),
        })

    priority = {
        "growth_driver": 0,
        "bright_spot": 1,
        "headwind": 2,
        "decline": 3,
    }

    stories.sort(
        key=lambda story: (
            priority.get(story["type"], 99),
            -abs(_safe_number(story.get("impact"))),
            story.get("_depth", 0),
        )
    )

    counts = {}
    selected = []

    for story in stories:
        story_type = story["type"]

        if counts.get(story_type, 0) >= max_per_type:
            continue

        story.pop("_depth", None)
        selected.append(story)
        counts[story_type] = counts.get(story_type, 0) + 1

    return selected


def _classify_review_story(node):
    classification = node.get("classification") or {}
    metrics = node.get("metrics") or {}

    impact = _safe_number(node.get("impact"))
    health = classification.get("health")
    valence = classification.get("valence")
    vs_business_rate = _safe_optional_number(
        metrics.get("vs_business_rate")
    )
    rate_change = _safe_optional_number(
        metrics.get("rate_change")
    )

    if (
        node.get("driver_type") == "mature"
        and impact > 0
        and vs_business_rate is not None
        and vs_business_rate >= 0.5
    ):
        return "bright_spot"

    if (
        health in {"weakening", "declining"}
        or (
            rate_change is not None
            and rate_change <= -0.15
        )
    ):
        return "headwind"

    if impact < 0:
        return "decline"

    if impact > 0 and valence == "contributing":
        return "growth_driver"

    return None


def _build_additional_stories(stories):
    return [
        {
            **story,
            "visual": _story_visual(story),
        }
        for story in stories
        if story.get("type") in {
            "bright_spot",
            "headwind",
            "decline",
        }
    ]


def _story_visual(story):
    metrics = story.get("metrics") or {}

    if story.get("type") == "bright_spot":
        current = _safe_optional_number(
            metrics.get("rate_current")
        )
        benchmark = _safe_optional_number(
            metrics.get("business_rate_current")
        )

        if current is not None and benchmark is not None:
            return {
                "type": "benchmark_bar",
                "metric": "velocity",
                "current": current,
                "benchmark": benchmark,
            }

    return None


# ---------------------------------------------------------------------------
# DISTRIBUTION
# ---------------------------------------------------------------------------

def _build_distribution_summary(df, current_start, current_end):
    if df is None or df.empty or "month_year" not in df.columns:
        return {}

    current_df = df[
        (df["month_year"] >= current_start)
        & (df["month_year"] <= current_end)
    ].copy()

    summary = {}

    if "coded_customer" in current_df.columns:
        summary["buying_stores"] = int(
            current_df["coded_customer"].nunique()
        )

    if "chain" in current_df.columns:
        summary["chains"] = int(
            current_df["chain"].nunique()
        )

    if "sku" in current_df.columns:
        summary["skus"] = int(
            current_df["sku"].nunique()
        )

    if "state" in current_df.columns:
        summary["states"] = int(
            current_df["state"].nunique()
        )

    if "dc" in current_df.columns:
        summary["dcs"] = int(
            current_df["dc"].nunique()
        )

    return summary


# ---------------------------------------------------------------------------
# WITHIN-PERIOD SIGNAL HELPERS
# ---------------------------------------------------------------------------

def _build_launch_health(stories, top_n=3):
    ramping = [
        story
        for story in stories
        if story.get("driver_type") == "ramping"
        and _extract_reorder_rate(story) is not None
    ]

    if not ramping:
        return None

    overall = next(
        (
            story
            for story in ramping
            if not story.get("scope")
        ),
        None,
    )

    if overall is None:
        return None

    retailer_stories = [
        story
        for story in ramping
        if story.get("scope", {}).get("chain")
    ]

    retailer_stories = sorted(
        retailer_stories,
        key=lambda story: _extract_reorder_rate(story) or 0,
        reverse=True,
    )[:top_n]

    return {
        "value": _extract_reorder_rate(overall),
        "label": overall.get("headline"),
        "supporting": [
            {
                "chain": story["scope"]["chain"],
                "value": _extract_reorder_rate(story),
                "headline": story.get("headline"),
                "detail": story.get("detail"),
            }
            for story in retailer_stories
        ],
    }


def _extract_reorder_rate(story):
    metrics = story.get("metrics") or {}

    for key in [
        "reorder_rate",
        "reorder_breadth",
        "placement_reorder_rate",
    ]:
        value = _safe_optional_number(metrics.get(key))

        if value is not None:
            return value

    headline = story.get("headline") or ""

    if "%" in headline and "reorder" in headline.lower():
        try:
            pct = float(
                headline.split("%")[0].split()[-1]
            )
            return pct / 100
        except (ValueError, IndexError):
            pass

    return None


# ---------------------------------------------------------------------------
# GENERIC HELPERS
# ---------------------------------------------------------------------------

def _serialize_period(period):
    if not period:
        return None

    return {
        "label": period.get("label"),
        "start": (
            str(period.get("start"))
            if period.get("start") is not None
            else None
        ),
        "end": (
            str(period.get("end"))
            if period.get("end") is not None
            else None
        ),
    }


def _find_scorecard_metric(scorecard, metric):
    return next(
        (
            row
            for row in scorecard
            if row.get("metric") == metric
        ),
        None,
    )


def _largest_positive_driver(growth_decomposition):
    positive = [
        row
        for row in growth_decomposition
        if _safe_number(row.get("impact")) > 0
    ]

    if not positive:
        return None

    return max(
        positive,
        key=lambda row: _safe_number(row.get("impact")),
    )


def _get_driver_nodes(tree):
    if tree is None:
        return []

    if isinstance(tree, list):
        if all(
            isinstance(node, dict)
            and node.get("node_type") == "driver"
            for node in tree
        ):
            return tree

        drivers = []

        for node in tree:
            if not isinstance(node, dict):
                continue

            if node.get("node_type") == "driver":
                drivers.append(node)

            elif node.get("node_type") == "root":
                drivers.extend(
                    child
                    for child in node.get("children", [])
                    if isinstance(child, dict)
                    and child.get("node_type") == "driver"
                )

        return drivers

    if isinstance(tree, dict):
        if tree.get("node_type") == "driver":
            return [tree]

        direct = [
            child
            for child in tree.get("children", [])
            if isinstance(child, dict)
            and child.get("node_type") == "driver"
        ]

        if direct:
            return direct

        for value in tree.values():
            if isinstance(value, (dict, list)):
                found = _get_driver_nodes(value)

                if found:
                    return found

    return []


def _flatten_tree(tree, depth=0):
    if tree is None:
        return []

    if isinstance(tree, list):
        flattened = []

        for node in tree:
            flattened.extend(
                _flatten_tree(node, depth)
            )

        return flattened

    if not isinstance(tree, dict):
        return []

    node = dict(tree)
    node["_depth"] = depth

    flattened = [node]

    for child in tree.get("children", []) or []:
        flattened.extend(
            _flatten_tree(child, depth + 1)
        )

    return flattened


def _group_units(df, group_cols, value_name):
    if df.empty:
        return pd.DataFrame(
            columns=group_cols + [value_name]
        )

    return (
        df.groupby(
            group_cols,
            dropna=False,
            as_index=False,
        )
        .agg(**{value_name: ("units", "sum")})
    )


def _calculate_grouped_vpo(
    df_filtered,
    df_full,
    group_cols,
    selected_months,
    value_name,
):
    if df_filtered.empty:
        return pd.DataFrame(
            columns=group_cols + [value_name]
        )

    result = calculate_vpo(
        df_filtered=df_filtered,
        df_full=df_full,
        group_cols=group_cols,
        selected_months=selected_months,
    )

    if not isinstance(result, pd.DataFrame) or result.empty:
        return pd.DataFrame(
            columns=group_cols + [value_name]
        )

    metric_col = (
        "vpo"
        if "vpo" in result.columns
        else "value"
        if "value" in result.columns
        else None
    )

    if metric_col is None:
        return pd.DataFrame(
            columns=group_cols + [value_name]
        )

    return result[
        group_cols + [metric_col]
    ].rename(
        columns={metric_col: value_name}
    )


def _to_dataframe(value):
    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value.copy()

    if isinstance(value, list):
        return pd.DataFrame(value)

    if isinstance(value, dict):
        return pd.DataFrame([value])

    return pd.DataFrame()


def _records(df):
    if df is None or df.empty:
        return []

    records = df.to_dict("records")

    return [
        {
            key: _clean_value(value)
            for key, value in record.items()
        }
        for record in records
    ]


def _clean_value(value):
    if isinstance(value, pd.Period):
        return str(value)

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    return value


def _pct_change(current, prior):
    current = _safe_optional_number(current)
    prior = _safe_optional_number(prior)

    if current is None or prior is None or prior == 0:
        return None

    return (current - prior) / prior


def _safe_number(value):
    value = _safe_optional_number(value)
    return 0 if value is None else value


def _safe_optional_number(value):
    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(value) or math.isinf(value):
        return None

    return value


def _display_driver(driver):
    if not driver:
        return "Other"

    return str(driver).replace("_", " ").title()


def _store_label(row):
    for key in [
        "customer_name",
        "coded_customer",
    ]:
        if row.get(key):
            return row[key]

    return "Store"