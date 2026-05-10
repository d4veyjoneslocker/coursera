import pandas as pd
from backend.insights.diagnostics import get_root_cause_concentration, describe_root_cause_signal
from backend.metrics.metric_growth_rates import calculate_reorder_rate_3m
from backend.insights.insights_helper import get_last_full_month
from backend.insights.insights_helper import format_pct, format_number, format_float, build_filter_context
from backend.metrics.metric_calculators import calculate_store_table_vpo, calculate_revenue, calculate_units

def _build_chain_store_status_table(df: pd.DataFrame) -> pd.DataFrame:
    # pulls 

    """
    Creates one row per chain x store with the status fields needed for
    chain struggling analysis.

    This becomes the centralized source of truth for both the insight and
    the struggling-store drilldown.
    """
    table = df.copy()

    store_status = (
        table.groupby(["chain", "coded_customer"], as_index=False)
        .agg(
            status=("status", "first"),
            last_month_purchased=("last_month_purchased", "first"),
        )
    )

    return store_status


def _calculate_chain_struggling_rates(
    store_status: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rolls store-level status up to the chain level and calculates:
    - struggling stores
    - total stores
    - struggling %
    - overall struggling %
    - variance vs average
    """
    counts = (
        store_status.groupby(["chain", "status"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    if "Struggling" not in counts.columns:
        counts["Struggling"] = 0

    status_cols = [col for col in counts.columns if col != "chain"]

    counts["total_stores"] = counts[status_cols].sum(axis=1)
    counts["struggling_stores"] = counts["Struggling"]

    counts["struggling_pct"] = (
        counts["struggling_stores"] / counts["total_stores"]
    )

    total_stores = counts["total_stores"].sum()
    total_struggling = counts["struggling_stores"].sum()

    overall_pct = total_struggling / total_stores if total_stores > 0 else 0

    counts["overall_struggling_pct"] = overall_pct
    counts["vs_avg"] = counts["struggling_pct"] - counts["overall_struggling_pct"]

    return counts[
        [
            "chain",
            "total_stores",
            "struggling_stores",
            "struggling_pct",
            "overall_struggling_pct",
            "vs_avg",
        ]
    ]


def _attach_latest_order_context(
    chain_table: pd.DataFrame,
    store_status: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adds latest-order context for struggling stores within each chain:
    - latest_month_purchased among struggling stores
    - number of struggling stores that last ordered in that latest month
    - formatted display month
    """
    struggling_store_status = store_status[
        store_status["status"] == "Struggling"
    ].copy()

    if struggling_store_status.empty:
        chain_table["latest_month_purchased"] = pd.NaT
        chain_table["latest_order_store_count"] = 0
        return chain_table

    latest_months = (
        struggling_store_status.groupby("chain", as_index=False)
        .agg(latest_month_purchased=("last_month_purchased", "max"))
    )

    latest_counts = struggling_store_status.merge(
        latest_months,
        on=["chain", "latest_month_purchased"],
        how="inner",
    )

    latest_counts = (
        latest_counts.groupby("chain", as_index=False)
        .agg(latest_order_store_count=("coded_customer", "nunique"))
    )

    result = chain_table.merge(latest_months, on="chain", how="left")
    result = result.merge(latest_counts, on="chain", how="left")

    result["latest_order_store_count"] = (
        result["latest_order_store_count"].fillna(0).astype(int)
    )

    return result

def _attach_chain_reorder_retention_context(
    chain_table: pd.DataFrame,
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adds chain-level reorder-rate deterioration context.

    Compares current 3-month reorder rate vs the same metric
    six months prior.
    """
    current_month = get_last_full_month()
    prior_month = current_month - 6

    reorder = calculate_reorder_rate_3m(df_filtered=df, df_full=df_all_time, group_cols=["chain"],)

    current_reorder = (
        reorder[reorder["month_year"] == current_month]
        .rename(columns={"reorder_rate_3m": "reorder_rate_3m_current"})
        [["chain", "reorder_rate_3m_current"]]
    )

    prior_reorder = (
        reorder[reorder["month_year"] == prior_month]
        .rename(columns={"reorder_rate_3m": "reorder_rate_3m_prior_6m"})
        [["chain", "reorder_rate_3m_prior_6m"]]
    )

    reorder_context = current_reorder.merge(
        prior_reorder,
        on="chain",
        how="left",
    )

    reorder_context["reorder_rate_3m_change_6m"] = (reorder_context["reorder_rate_3m_current"] - reorder_context["reorder_rate_3m_prior_6m"])

    return chain_table.merge(
        reorder_context,
        on="chain",
        how="left",
    )


def _attach_chain_root_cause_context(
    chain_table: pd.DataFrame,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adds diagnostic root-cause context for each chain.

    Uses the original filtered df because root cause needs row-level fields
    like sku/state, while chain_table/store_status only has one row per store.
    """
    root_causes = []

    for chain in chain_table["chain"]:
        struggling_rows = df[
            (df["chain"] == chain)
            & (df["status"] == "Struggling")
        ].copy()

        chain_universe = df[df["chain"] == chain].copy()

        root_cause = get_root_cause_concentration(
            affected_df=struggling_rows,
            universe_df=chain_universe,
            dimensions=["sku", "state"],
        )

        root_cause_text = describe_root_cause_signal(root_cause)

        root_causes.append({
            "chain": chain,
            "root_cause": root_cause,
            "root_cause_text": root_cause_text,
        })

    root_cause_table = pd.DataFrame(root_causes)

    return chain_table.merge(root_cause_table, on="chain", how="left")


def build_chain_struggling_table(
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
) -> pd.DataFrame:
    """
    Builds the analytical table for the chain struggling insight.

    This table should be the single source of truth for:
    - insight selection
    - narrative metrics
    - CTA/store-list alignment
    """

    
    store_status = _build_chain_store_status_table(df)

    chain_table = _calculate_chain_struggling_rates(store_status)

    chain_table = _attach_latest_order_context(
        chain_table=chain_table,
        store_status=store_status,
    )

    chain_table = _attach_chain_reorder_retention_context(
        chain_table=chain_table,
        df=df,
        df_all_time=df_all_time,
    )

    chain_table = _attach_chain_root_cause_context(
        chain_table=chain_table,
        df=df,
    )

    return chain_table

def analyze_chain_struggling(
    table: pd.DataFrame,
    limit: int = 1,
) -> pd.DataFrame | None:
    """
    Applies insight criteria and selects the strongest
    struggling-chain risks.
    """
    table = table.copy()

    if table.empty:
        return None

    required_cols = [
        "chain",
        "total_stores",
        "struggling_stores",
        "struggling_pct",
        "overall_struggling_pct",
        "vs_avg",
    ]

    missing_cols = [col for col in required_cols if col not in table.columns]

    if missing_cols:
        return None

    # REMOVE CONFIDENTIAL / NON-REAL CHAINS
    table = table[
        table["chain"].notna()
        & ~table["chain"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("CONFIDENTIAL")
    ].copy()

    # INSIGHT CRITERIA
    table = table[
        (table["total_stores"] >= 10)
        & (table["struggling_stores"] > 0)
        & (table["struggling_pct"].notna())
        & (table["vs_avg"].notna())
        & (table["vs_avg"] > 0.05)
    ].copy()

    if table.empty:
        return None

    # SELECT TOP CHAINS
    table = table.sort_values(
        ["struggling_pct", "struggling_stores"],
        ascending=[False, False],
    )

    return table.head(limit)

def normalize_chain_struggling_data(
    table: pd.DataFrame,
) -> list[dict] | dict | None:
    """
    Normalizes analyzed chain-struggling rows into
    structured insight-ready data objects.
    """
    if table is None or table.empty:
        return None

    results = []

    for _, row in table.iterrows():

        result = {
            "chain": row["chain"],

            "struggling_stores": int(row["struggling_stores"]),
            "total_stores": int(row["total_stores"]),

            "struggling_pct": float(row["struggling_pct"]),
            "overall_struggling_pct": float(row["overall_struggling_pct"]),
            "vs_avg": float(row["vs_avg"]),

            "latest_month_purchased": row.get("latest_month_purchased"),

            "latest_order_store_count": int(
                row.get("latest_order_store_count", 0) or 0
            ),

            "reorder_rate_3m_current": row.get(
                "reorder_rate_3m_current"
            ),

            "reorder_rate_3m_prior_6m": row.get(
                "reorder_rate_3m_prior_6m"
            ),

            "reorder_rate_3m_change_6m": row.get(
                "reorder_rate_3m_change_6m"
            ),

            "root_cause": row.get("root_cause"),
            "root_cause_text": row.get("root_cause_text"),

            "metrics": {
                "struggling_stores": int(row["struggling_stores"]),
                "total_stores": int(row["total_stores"]),
                "struggling_pct": float(row["struggling_pct"]),
                "overall_struggling_pct": float(row["overall_struggling_pct"]),
                "vs_avg": float(row["vs_avg"]),

                "latest_order_store_count": int(
                    row.get("latest_order_store_count", 0) or 0
                ),

                "reorder_rate_3m_current": row.get(
                    "reorder_rate_3m_current"
                ),

                "reorder_rate_3m_prior_6m": row.get(
                    "reorder_rate_3m_prior_6m"
                ),

                "reorder_rate_3m_change_6m": row.get(
                    "reorder_rate_3m_change_6m"
                ),
            },

            "entities": {
                "chain": row["chain"],
            },
        }

        results.append(result)

    if len(results) == 1:
        return results[0]

    return results

def describe_chain_struggling(data, filters=None):
    if data is None:
        return None

    chain = data["chain"]

    struggling_stores = data["struggling_stores"]
    total_stores = data["total_stores"]

    struggling_pct = data["struggling_pct"]
    vs_avg = data["vs_avg"]

    latest_month = data.get("latest_month_purchased")
    latest_order_store_count = data.get(
        "latest_order_store_count"
    )

    reorder_current = data.get(
        "reorder_rate_3m_current"
    )

    reorder_prior = data.get(
        "reorder_rate_3m_prior_6m"
    )

    reorder_change = data.get(
        "reorder_rate_3m_change_6m"
    )

    root_cause_text = data.get("root_cause_text")

    context_str, context_parts = build_filter_context(
        filters,
        exclude_keys={"chain", "status"},
    )

    # FORMAT METRICS

    struggling_pct_fmt = format_pct(struggling_pct)

    vs_avg_fmt = format_pct(vs_avg, signed=True)

    struggling_stores_fmt = format_number(struggling_stores)

    total_stores_fmt = format_number(total_stores)

    latest_order_store_count_fmt = format_number(latest_order_store_count)

    reorder_current_fmt = format_pct(reorder_current)

    reorder_prior_fmt = format_pct(reorder_prior)

    # HEADLINE

    headline = (
        f"Retailer engagement may be weakening at {chain}."
    )

    # SUMMARY

    summary = (
        f"{chain} has {struggling_pct_fmt} of stores marked "
        f"as struggling{context_str}, "
        f"{vs_avg_fmt} pts vs your overall average."
    )

    # SUMMARY PARTS

    parts = [
        {
            "type": "chip",
            "value": chain,
            "tone": "neutral",
        },

        {
            "type": "text",
            "value": " has ",
        },

        {
            "type": "chip",
            "value": struggling_pct_fmt,
            "tone": "negative",
        },

        {
            "type": "text",
            "value": " of stores marked as struggling",
        },

        *context_parts,

        {
            "type": "text",
            "value": ", ",
        },

        {
            "type": "chip",
            "value": f"{vs_avg_fmt} pts",
            "tone": "negative",
        },

        {
            "type": "text",
            "value": " vs your overall average.",
        },
    ]

    # DESCRIPTION BLOCKS

    intro_block = {
        "type": "text",
        "value": (
            f"{chain} has {struggling_stores_fmt} of "
            f"{total_stores_fmt} stores marked as struggling, "
            f"or {struggling_pct_fmt} of its store base. "
            f"That is {vs_avg_fmt} pts above your overall average, "
            f"suggesting the issue is concentrated within this chain "
            f"rather than spread evenly across the business."
        ),
    }

    reorder_block = {
        "type": "text",
        "value": (
            f"Reorder behavior has also weakened: the chain’s "
            f"3-month reorder rate was {reorder_prior_fmt} "
            f"six months ago, compared with "
            f"{reorder_current_fmt} today."
        ),
    }

    latest_order_block = None

    if pd.notna(latest_month):

        latest_month_display = (
            latest_month.to_timestamp().strftime("%B %Y")
            if hasattr(latest_month, "to_timestamp")
            else pd.to_datetime(latest_month).strftime("%B %Y")
        )

        latest_order_block = {
            "type": "text",
            "value": (
                f"The most recent orders from this group came in "
                f"{latest_month_display}, with "
                f"{latest_order_store_count_fmt} stores "
                f"last ordering that month."
            ),
        }

    root_cause_block = {
        "type": "text",
        "value": root_cause_text,
    }

    # OPTIONAL BLOCK CONDITIONS

    include_reorder_block = (
        reorder_current is not None
        and reorder_prior is not None
        and reorder_change is not None
        and pd.notna(reorder_current)
        and pd.notna(reorder_prior)
        and pd.notna(reorder_change)
        and reorder_change < 0
    )

    include_latest_order_block = (
        latest_order_block is not None
    )

    include_root_cause_block = (
        root_cause_text is not None
        and root_cause_text != ""
    )

    # ASSEMBLE DESCRIPTION

    description = [
        intro_block,

        reorder_block
        if include_reorder_block
        else None,

        latest_order_block
        if include_latest_order_block
        else None,

        root_cause_block
        if include_root_cause_block
        else None,
    ]

    description = [
        block for block in description
        if block is not None
    ]

    return {
        "headline": headline,
        "summary": summary,
        "parts": parts,
        "description": description,
    }

def create_chain_struggling_store_list(
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
    chain: str,
) -> pd.DataFrame:
    """
    Returns struggling stores for the selected chain.

    Uses the same store-status helper as the chain-struggling insight
    so the insight count and drilldown list stay aligned.
    """
    grain = ["coded_customer", "chain"]

    store_status = _build_chain_store_status_table(df)

    table = store_status[
        (store_status["chain"] == chain)
        & (store_status["status"] == "Struggling")
    ].copy()

    if table.empty:
        return table

    store_month = (
        df.groupby(grain + ["month_year"], as_index=False)
        .agg(reordered=("reorder_flag", "max"))
    )

    reorders = (
        store_month.groupby(grain, as_index=False)
        .agg(reorders=("reordered", "sum"))
    )

    store_details = (
        df.groupby(grain, as_index=False)
        .agg(
            store_number=("store_number", "first"),
            street_address=("street_address", "first"),
            city=("city", "first"),
            state=("state", "first"),
            zip=("zip", "first"),
            first_month_purchased=("first_month_purchased", "first"),
            last_month_purchased=("last_month_purchased", "first"),
        )
    )

    revenue = calculate_revenue(df, grain)
    units = calculate_units(df, grain)
    vpo = calculate_store_table_vpo(df_all_time, group_cols=grain)

    result = (
        table[["coded_customer", "chain", "status"]]
        .merge(store_details, on=grain, how="left")
        .merge(reorders, on=grain, how="left")
        .merge(revenue, on=grain, how="left")
        .merge(units, on=grain, how="left")
        .merge(vpo, on=grain, how="left")
    )

    result["reorders"] = result["reorders"].fillna(0)

    columns = [
        "coded_customer",
        "chain",
        "store_number",
        "street_address",
        "city",
        "state",
        "zip",
        "units",
        "revenue",
        "vpo",
        "reorders",
        "first_month_purchased",
        "last_month_purchased",
        "status",
    ]

    existing_cols = [
        col for col in columns
        if col in result.columns
    ]

    return (
        result[existing_cols]
        .sort_values(
            ["last_month_purchased", "units"],
            ascending=[False, False],
        )
    )

def build_chain_struggling_insight(
    df: pd.DataFrame,
    df_all_time: pd.DataFrame,
    filters=None,
):
    table = build_chain_struggling_table(
        df=df,
        df_all_time=df_all_time,
    )

    analyzed = analyze_chain_struggling(table)

    data = normalize_chain_struggling_data(analyzed)

    description = describe_chain_struggling(
        data=data,
        filters=filters,
    )

    if data is None or description is None:
        return None

    chain = data["chain"]

    return {
        "type": "chain_struggling",
        "section": "at_risk",
        "priority": 20,

        **description,

        "metrics": data["metrics"],
        "entities": data["entities"],

        "chain": chain,
        "struggling_pct": data["struggling_pct"],

        "drilldown": {
            "label": "View struggling stores",
            "href": f"/insights/struggling_stores?chain={chain}",
        },
    }