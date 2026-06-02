import pandas as pd


def build_what_changed(df: pd.DataFrame, max_items: int = 4):
    if df is None or df.empty:
        return []

    table = df.copy()
    table["month_year"] = pd.PeriodIndex(table["month_year"], freq="M")

    current_month = pd.Timestamp.today().to_period("M")
    table = table[table["month_year"] != current_month].copy()

    if table.empty:
        return []

    latest_month = table["month_year"].max()
    prior_month = latest_month - 1

    changes = []

    for detector in [
        detect_top_sku_change,
        detect_top_chain_change,
        detect_new_store_expansion,
        detect_sku_new_states,
        #detect_chain_assortment_depth_gain,
    ]:
        change = detector(table, latest_month, prior_month)
        if change:
            changes.append(change)

    changes = sorted(
        changes,
        key=lambda x: x.get("priority", 999),
    )

    return changes[:max_items]


def detect_top_sku_change(df, latest_month, prior_month):
    current = _rank_by_units(df, latest_month, "sku")
    prior = _rank_by_units(df, prior_month, "sku")

    if current.empty or prior.empty:
        return None

    current_top = current.iloc[0]
    prior_top = prior.iloc[0]

    if current_top["sku"] == prior_top["sku"]:
        return None

    prior_rank_for_current = _find_rank(prior, "sku", current_top["sku"])

    rank_text = (
        f"moving from #{prior_rank_for_current} last month"
        if prior_rank_for_current
        else "after not ranking last month"
    )

    return {
        "type": "state_change",
        "priority": 1,
        "parts": [
            {"type": "sku_chip", "value": current_top["sku"]},
            {
                "type": "text",
                "value": (
                    f" became the #1 SKU by monthly units, {rank_text}, "
                    f"with {_format_number(current_top['units'])} units."
                ),
            },
        ],
        "drilldown": {
            "label": "View SKU rankings",
            "href": "/insights/sku_rankings",
        },
    }


def detect_top_chain_change(df, latest_month, prior_month):
    current = _rank_by_units(df, latest_month, "chain")
    prior = _rank_by_units(df, prior_month, "chain")

    if current.empty or prior.empty:
        return None

    current_top = current.iloc[0]
    prior_top = prior.iloc[0]

    if current_top["chain"] == prior_top["chain"]:
        return None

    prior_rank_for_current = _find_rank(prior, "chain", current_top["chain"])

    rank_text = (
        f"moving from #{prior_rank_for_current} last month"
        if prior_rank_for_current
        else "after not ranking last month"
    )

    return {
        "type": "state_change",
        "priority": 2,
        "parts": [
            {"type": "chain_chip", "value": current_top["chain"]},
            {
                "type": "text",
                "value": (
                    f" became the top chain by monthly units, {rank_text}, "
                    f"with {_format_number(current_top['units'])} units."
                ),
            },
        ],
    }


def detect_new_store_expansion(df, latest_month, prior_month):
    current = df[
        (df["month_year"] == latest_month)
        & (df["units"] > 0)
    ].copy()

    historical = df[
        (df["month_year"] < latest_month)
        & (df["units"] > 0)
    ].copy()

    if current.empty:
        return None

    current_pairs = current[
        ["sku", "coded_customer"]
    ].drop_duplicates()

    historical_pairs = historical[
        ["sku", "coded_customer"]
    ].drop_duplicates()

    historical_pairs["seen_before"] = True

    result = current_pairs.merge(
        historical_pairs,
        on=["sku", "coded_customer"],
        how="left",
    )

    result["is_new_store"] = result["seen_before"].isna()

    result = (
        result.groupby("sku", as_index=False)
        .agg(new_stores=("is_new_store", "sum"))
    )

    result = result[result["new_stores"] > 0].copy()

    if result.empty:
        return None

    top = result.sort_values(
        "new_stores",
        ascending=False,
    ).iloc[0]

    return {
        "type": "state_change",
        "priority": 3,
        "parts": [
            {"type": "sku_chip", "value": top["sku"]},
            {
                "type": "text",
                "value": (
                    f" added {_format_number(top['new_stores'])} new buying stores this month."
                ),
            },
        ],
        "drilldown": {
            "label": "View new store distribution",
            "href": f"/insights/new_store_distribution?sku={top['sku']}",
        },
    }

def detect_sku_new_states(df, latest_month, prior_month):
    if "state" not in df.columns:
        return None

    current = df[
        (df["month_year"] == latest_month)
        & (df["units"] > 0)
        & (df["state"].notna())
    ].copy()

    history = df[
        (df["month_year"] < latest_month)
        & (df["units"] > 0)
        & (df["state"].notna())
    ].copy()

    if current.empty:
        return None

    rows = []

    for sku, sku_current in current.groupby("sku"):
        current_states = set(sku_current["state"].dropna().astype(str))
        historical_states = set(
            history[history["sku"] == sku]["state"].dropna().astype(str)
        )

        new_states = sorted(current_states - historical_states)

        if new_states:
            rows.append({
                "sku": sku,
                "new_state_count": len(new_states),
                "new_states": new_states,
            })

    if not rows:
        return None

    top = sorted(
        rows,
        key=lambda x: x["new_state_count"],
        reverse=True,
    )[0]

    return {
        "type": "state_change",
        "priority": 4,
        "parts": [
            {"type": "sku_chip", "value": top["sku"]},
            {
                "type": "text",
                "value": (
                    f" entered {_format_number(top['new_state_count'])} new "
                    f"{'state' if top['new_state_count'] == 1 else 'states'} "
                    f"this month."
                ),
            },
        ],
        "drilldown": {
            "label": "View new state stores",
            "href": f"/insights/sku_state_expansion?sku={top['sku']}",
        },
    }


def detect_chain_assortment_depth_gain(df, latest_month, prior_month):
    current = _avg_skus_per_store(df, latest_month, "chain")
    prior = _avg_skus_per_store(df, prior_month, "chain")

    if current.empty or prior.empty:
        return None

    result = current.merge(
        prior,
        on="chain",
        how="left",
        suffixes=("_current", "_prior"),
    )

    result = result.dropna(subset=["avg_skus_per_store_prior"]).copy()

    if result.empty:
        return None

    result["avg_skus_gain"] = (
        result["avg_skus_per_store_current"]
        - result["avg_skus_per_store_prior"]
    )

    result = result[result["avg_skus_gain"] >= 0.3].copy()

    if result.empty:
        return None

    top = result.sort_values("avg_skus_gain", ascending=False).iloc[0]

    return {
        "type": "state_change",
        "priority": 5,
        "parts": [
            {"type": "chain_chip", "value": top["chain"]},
            {
                "type": "text",
                "value": (
                    f" increased assortment depth from "
                    f"{_format_float(top['avg_skus_per_store_prior'])} to "
                    f"{_format_float(top['avg_skus_per_store_current'])} "
                    f"SKUs per active store."
                ),
            },
        ],
    }


def _rank_by_units(df, month, grain):
    month_df = df[
        (df["month_year"] == month)
        & (df["units"] > 0)
    ].copy()

    if month_df.empty or grain not in month_df.columns:
        return pd.DataFrame()

    result = (
        month_df.groupby(grain, as_index=False)
        .agg(units=("units", "sum"))
        .sort_values("units", ascending=False)
        .reset_index(drop=True)
    )

    result["rank"] = result.index + 1

    return result


def _active_stores_by(df, month, grain):
    month_df = df[
        (df["month_year"] == month)
        & (df["units"] > 0)
    ].copy()

    if month_df.empty or grain not in month_df.columns:
        return pd.DataFrame()

    return (
        month_df.groupby(grain, as_index=False)
        .agg(active_stores=("coded_customer", "nunique"))
    )


def _avg_skus_per_store(df, month, grain):
    month_df = df[
        (df["month_year"] == month)
        & (df["units"] > 0)
    ].copy()

    if month_df.empty or grain not in month_df.columns:
        return pd.DataFrame()

    store_sku_counts = (
        month_df.groupby([grain, "coded_customer"], as_index=False)
        .agg(sku_count=("sku", "nunique"))
    )

    return (
        store_sku_counts.groupby(grain, as_index=False)
        .agg(avg_skus_per_store=("sku_count", "mean"))
    )


def _find_rank(ranking_df, grain, value):
    match = ranking_df[ranking_df[grain] == value]

    if match.empty:
        return None

    return int(match.iloc[0]["rank"])


def _format_number(value):
    if value is None or pd.isna(value):
        return "—"

    return f"{float(value):,.0f}"


def _format_float(value):
    if value is None or pd.isna(value):
        return "—"

    return f"{float(value):.1f}"