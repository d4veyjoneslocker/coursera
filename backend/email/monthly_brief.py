import pandas as pd
from backend.data_pipeline.table_loader import (
    load_org_tables,
    load_active_pods,
    load_fill_rate_df,
)
from backend.deep_dive.digest_builder import (
    build_weekly_digest,
    make_json_safe,
)
from backend.metrics.kpis.build_kpis import build_kpis
from backend.metrics.metric_tables import chain_table
from backend.metrics.fill_rate.metrics import (
    fill_rate_metrics,
)
from backend.insights.diagnostics import analyze_fill_rate_impact
# ---------------------------------------------------------
# BUSINESS NARRATIVE
# ---------------------------------------------------------
from backend.insights.business_review.business_review import (
    run_business_review,
)
# ---------------------------------------------------------
# INVENTORY
# ---------------------------------------------------------
from backend.serving.routes.inventory.inventory import (
    get_inventory_overview,
)
def _get_digest_section(digest, key):
    """
    Pull one section's insights from the existing digest output.
    """
    for section in digest.get("sections", []):
        if section.get("key") == key:
            return section.get("insights", [])
    return []
def _df_to_records(df):
    """
    Safely convert a DataFrame to JSON-safe records.
    """
    if df is None or df.empty:
        return []
    return make_json_safe(
        df.to_dict(orient="records")
    )
def build_monthly_brief(
    org_id: str,
    end_month: str | pd.Period | None = None,
):
    """
    Build the raw data payload for SKUba's monthly email brief.
    V0 goal:
        \- One brand
        \- One completed reporting month
        \- Reuse canonical SKUba analytics
        \- No email formatting yet
        \- Return enough information to curate the actual email
    Parameters
    \----------
    org_id:
        SKUba organization ID.
    end_month:
        Month to treat as the reporting month.
        Example:
            "2026-09"
        If None, uses the latest completed month available
        in the sales data.
    """
    # =========================================================
    # LOAD CANONICAL DATA
    # =========================================================
    features_df = load_org_tables(org_id).copy()
    active_pods_full = load_active_pods(org_id).copy()
    fill_rate_df = load_fill_rate_df(org_id).copy()
    features_df["month_year"] = pd.PeriodIndex(
        features_df["month_year"],
        freq="M",
    )
    active_pods_full["month_year"] = pd.PeriodIndex(
        active_pods_full["month_year"],
        freq="M",
    )
    if not fill_rate_df.empty:
        fill_rate_df["month_year"] = pd.PeriodIndex(
            fill_rate_df["month_year"],
            freq="M",
        )
    # =========================================================
    # RESOLVE REPORTING MONTH
    # =========================================================
    if end_month is not None:
        end_month = pd.Period(
            end_month,
            freq="M",
        )
    else:
        current_month = pd.Timestamp.today().to_period("M")
        completed_sales = features_df[
            features_df["month_year"] < current_month
        ]
        if completed_sales.empty:
            raise ValueError(
                "No completed sales month available."
            )
        end_month = completed_sales["month_year"].max()
    # Never allow future sales history into the brief.
    df_full = features_df[
        features_df["month_year"] <= end_month
    ].copy()
    if df_full.empty:
        raise ValueError(
            f"No sales data found through {end_month}."
        )
    # Current reporting month.
    df = df_full[
        df_full["month_year"] == end_month
    ].copy()
    if df.empty:
        raise ValueError(
            f"No sales data found for {end_month}."
        )
    # Active POD history through reporting month.
    active_pods_df = active_pods_full[
        active_pods_full["month_year"] <= end_month
    ].copy()
    # Fill-rate history through reporting month.
    fill_rate_full = fill_rate_df[
        fill_rate_df["month_year"] <= end_month
    ].copy()
    fill_rate_current = fill_rate_full[
        fill_rate_full["month_year"] == end_month
    ].copy()
    # =========================================================
    # 1. MONTH AT A GLANCE
    # =========================================================
    kpis = build_kpis(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        active_pods_full=active_pods_full,
        end_month=end_month,
    )
    # =========================================================
    # 2. BUSINESS NARRATIVE
    #
    # Build BOTH comparison lenses:
    #
    #   PP = L3M vs previous 3 months
    #   PY = L3M vs same 3 months prior year
    #
    # The email curation layer can then decide whether the
    # sequential or year-over-year view is more informative.
    # =========================================================

    business_review_pp = run_business_review(
        features_df=df_full,
        active_pods_df=active_pods_df,
        period="L3M",
        year=end_month.year,
        comparison="PP",
    )

    business_review_py = run_business_review(
        features_df=df_full,
        active_pods_df=active_pods_df,
        period="L3M",
        year=end_month.year,
        comparison="PY",
    )

    business_narrative_pp = business_review_pp["narrative_tree"]
    business_narrative_py = business_review_py["narrative_tree"]

    business_review_metrics_pp = business_review_pp["review"]
    business_review_metrics_py = business_review_py["review"]

    business_review_periods_pp = {
        "current_period": business_review_pp["current_period"],
        "prior_period": business_review_pp["prior_period"],
    }

    business_review_periods_py = {
        "current_period": business_review_py["current_period"],
        "prior_period": business_review_py["prior_period"],
    }

    # =========================================================
    # 3. SKUba INSIGHTS
    #
    # The digest remains useful as a canonical source for
    # opportunities / risks / other insight modules.
    #
    # It is NOT the source of the business narrative.
    # =========================================================
    digest = build_weekly_digest(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        active_pods_full=active_pods_full,
        filters={},
    )
    what_changed = _get_digest_section(
        digest,
        "what_changed",
    )
    opportunities = _get_digest_section(
        digest,
        "opportunities",
    )
    risks = _get_digest_section(
        digest,
        "at_risk",
    )
    # =========================================================
    # 4. FILL RATE — MONTH SNAPSHOT
    # =========================================================
    fill_rate_summary = []
    fill_rate_by_chain = []
    fill_rate_by_dc = []
    fill_rate_by_chain_sku = []
    if not fill_rate_current.empty:
        fill_rate_summary = _df_to_records(
            fill_rate_metrics(
                fill_rate_current,
                grain=None,
            )
        )
        if "chain" in fill_rate_current.columns:
            fill_rate_by_chain = _df_to_records(
                fill_rate_metrics(
                    fill_rate_current,
                    grain=["chain"],
                ).sort_values(
                    "fill_rate",
                    ascending=True,
                )
            )
        if "dc" in fill_rate_current.columns:
            fill_rate_by_dc = _df_to_records(
                fill_rate_metrics(
                    fill_rate_current,
                    grain=["dc"],
                ).sort_values(
                    "fill_rate",
                    ascending=True,
                )
            )
        if {
            "chain",
            "sku",
        }.issubset(fill_rate_current.columns):
            fill_rate_by_chain_sku = _df_to_records(
                fill_rate_metrics(
                    fill_rate_current,
                    grain=[
                        "chain",
                        "sku",
                    ],
                ).sort_values(
                    "fill_rate",
                    ascending=True,
                )
            )
    # =========================================================
    # 5. ORDERING + FULFILLMENT IMPACT
    #
    # Keep BOTH comparison lenses for BOTH horizons:
    #
    #   L3M / PP = current 3 months vs previous 3 months
    #   L3M / PY = current 3 months vs same period prior year
    #   L1M / PP = current month vs previous month
    #   L1M / PY = current month vs same month prior year
    #
    # The email does not need to show all four. The curation
    # layer can use whichever lens adds useful context.
    #
    # NOTE:
    # Current-month ordering is useful immediately, while
    # current-month fulfillment may still be incomplete.
    # =========================================================

    fill_rate_impact_l3m_pp_overall = []
    fill_rate_impact_l3m_pp_by_chain = []
    fill_rate_impact_l3m_py_overall = []
    fill_rate_impact_l3m_py_by_chain = []

    fill_rate_impact_l1m_pp_overall = []
    fill_rate_impact_l1m_pp_by_chain = []
    fill_rate_impact_l1m_py_overall = []
    fill_rate_impact_l1m_py_by_chain = []

    fill_rate_timeline = []

    if not fill_rate_full.empty:

        (
            impact_l3m_pp_overall,
            timeline_overall,
        ) = analyze_fill_rate_impact(
            sales_df=df_full,
            fill_rate_df=fill_rate_full,
            active_pods_df=active_pods_df,
            period="L3M",
            comparison="PP",
            group_cols=[],
            end_month=end_month,
        )

        fill_rate_impact_l3m_pp_overall = _df_to_records(
            impact_l3m_pp_overall
        )
        fill_rate_timeline = _df_to_records(
            timeline_overall
        )

        if "chain" in fill_rate_full.columns:
            (
                impact_l3m_pp_chain,
                _,
            ) = analyze_fill_rate_impact(
                sales_df=df_full,
                fill_rate_df=fill_rate_full,
                active_pods_df=active_pods_df,
                period="L3M",
                comparison="PP",
                group_cols=["chain"],
                end_month=end_month,
            )
            fill_rate_impact_l3m_pp_by_chain = _df_to_records(
                impact_l3m_pp_chain
            )

        (
            impact_l3m_py_overall,
            _,
        ) = analyze_fill_rate_impact(
            sales_df=df_full,
            fill_rate_df=fill_rate_full,
            active_pods_df=active_pods_df,
            period="L3M",
            comparison="PY",
            group_cols=[],
            end_month=end_month,
        )

        fill_rate_impact_l3m_py_overall = _df_to_records(
            impact_l3m_py_overall
        )

        if "chain" in fill_rate_full.columns:
            (
                impact_l3m_py_chain,
                _,
            ) = analyze_fill_rate_impact(
                sales_df=df_full,
                fill_rate_df=fill_rate_full,
                active_pods_df=active_pods_df,
                period="L3M",
                comparison="PY",
                group_cols=["chain"],
                end_month=end_month,
            )
            fill_rate_impact_l3m_py_by_chain = _df_to_records(
                impact_l3m_py_chain
            )

        (
            impact_l1m_pp_overall,
            _,
        ) = analyze_fill_rate_impact(
            sales_df=df_full,
            fill_rate_df=fill_rate_full,
            active_pods_df=active_pods_df,
            period="L1M",
            comparison="PP",
            group_cols=[],
            end_month=end_month,
        )

        fill_rate_impact_l1m_pp_overall = _df_to_records(
            impact_l1m_pp_overall
        )

        if "chain" in fill_rate_full.columns:
            (
                impact_l1m_pp_chain,
                _,
            ) = analyze_fill_rate_impact(
                sales_df=df_full,
                fill_rate_df=fill_rate_full,
                active_pods_df=active_pods_df,
                period="L1M",
                comparison="PP",
                group_cols=["chain"],
                end_month=end_month,
            )
            fill_rate_impact_l1m_pp_by_chain = _df_to_records(
                impact_l1m_pp_chain
            )

        (
            impact_l1m_py_overall,
            _,
        ) = analyze_fill_rate_impact(
            sales_df=df_full,
            fill_rate_df=fill_rate_full,
            active_pods_df=active_pods_df,
            period="L1M",
            comparison="PY",
            group_cols=[],
            end_month=end_month,
        )

        fill_rate_impact_l1m_py_overall = _df_to_records(
            impact_l1m_py_overall
        )

        if "chain" in fill_rate_full.columns:
            (
                impact_l1m_py_chain,
                _,
            ) = analyze_fill_rate_impact(
                sales_df=df_full,
                fill_rate_df=fill_rate_full,
                active_pods_df=active_pods_df,
                period="L1M",
                comparison="PY",
                group_cols=["chain"],
                end_month=end_month,
            )
            fill_rate_impact_l1m_py_by_chain = _df_to_records(
                impact_l1m_py_chain
            )

    # =========================================================
    # 6. CHAIN PERFORMANCE
    # =========================================================
    chains = chain_table(
        df=df,
        df_full=df_full,
        active_pods_df=active_pods_df,
        active_pods_full=active_pods_full,
        end_month=end_month,
    )
    chain_records = _df_to_records(
        chains
    )
    # =========================================================
    # 7. INVENTORY
    #
    # Inventory is intentionally CURRENT / FORWARD-LOOKING.
    #
    # Unlike the sales narrative, we do NOT constrain this to
    # September. The October 1 brief should tell the brand what
    # its inventory situation looks like NOW based on the latest
    # inventory / PO information available.
    #
    # Reuse the canonical inventory overview rather than
    # duplicating inventory calculations here.
    # =========================================================
    inventory = get_inventory_overview(
        org_id=org_id,
    )
    # =========================================================
    # FINAL RAW MONTHLY BRIEF
    # =========================================================
    brief = {
        "meta": {
            "org_id": org_id,
            "report_month": str(end_month),
            "report_month_label": end_month.strftime(
                "%B %Y"
            ),
        },
        # -----------------------------------------------------
        # FACTUAL SNAPSHOT
        # -----------------------------------------------------
        "at_a_glance": kpis,
        # -----------------------------------------------------
        # BUSINESS NARRATIVE
        #
        # Canonical NEW / RAMPING / MATURE explanation.
        # -----------------------------------------------------
        "business_narrative": {
            "primary": {
                "period": "L3M",
                "comparison": "PP",
                "periods": business_review_periods_pp,
                "review": business_review_metrics_pp,
                "narrative_tree": business_narrative_pp,
            },
            "year_over_year": {
                "period": "L3M",
                "comparison": "PY",
                "periods": business_review_periods_py,
                "review": business_review_metrics_py,
                "narrative_tree": business_narrative_py,
            },
        },
        # -----------------------------------------------------
        # OTHER SKUba INSIGHTS
        # -----------------------------------------------------
        "what_changed": what_changed,
        "opportunities": opportunities,
        "risks": risks,
        # -----------------------------------------------------
        # OPERATIONS
        # -----------------------------------------------------
        "inventory": inventory,
        "fill_rate": {
            "summary": fill_rate_summary,
            "by_chain": fill_rate_by_chain,
            "by_dc": fill_rate_by_dc,
            "by_chain_sku": fill_rate_by_chain_sku,
            "impact_l3m": {
                "previous_period": {
                    "period": "L3M",
                    "comparison": "PP",
                    "overall": fill_rate_impact_l3m_pp_overall,
                    "by_chain": fill_rate_impact_l3m_pp_by_chain,
                },
                "prior_year": {
                    "period": "L3M",
                    "comparison": "PY",
                    "overall": fill_rate_impact_l3m_py_overall,
                    "by_chain": fill_rate_impact_l3m_py_by_chain,
                },
            },
            "impact_l1m": {
                "previous_period": {
                    "period": "L1M",
                    "comparison": "PP",
                    "overall": fill_rate_impact_l1m_pp_overall,
                    "by_chain": fill_rate_impact_l1m_pp_by_chain,
                },
                "prior_year": {
                    "period": "L1M",
                    "comparison": "PY",
                    "overall": fill_rate_impact_l1m_py_overall,
                    "by_chain": fill_rate_impact_l1m_py_by_chain,
                },
            },
            "timeline": fill_rate_timeline,
        },
        # -----------------------------------------------------
        # SUPPORTING PERFORMANCE DATA
        # -----------------------------------------------------
        "chains": chain_records,
    }
    return make_json_safe(
        brief
    )