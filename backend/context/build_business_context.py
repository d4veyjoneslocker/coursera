import pandas as pd

def detect_retailer_launches(
    df: pd.DataFrame,
    min_stores_added: int = 25,
) -> list[dict]:

    monthly = (
        df.groupby(["chain", "month_year"])["coded_customer"]
        .nunique()
        .reset_index(name="buying_stores")
        .sort_values(["chain", "month_year"])
    )

    monthly["buying_stores_prior"] = monthly.groupby("chain")["buying_stores"].shift(1).fillna(0)
    monthly["stores_added"] = monthly["buying_stores"] - monthly["buying_stores_prior"]

    launches = monthly[monthly["stores_added"] >= min_stores_added]

    records = []

    for _, row in launches.iterrows():
        records.append({
            "context_type": "recent_retailer_launch",
            "scope": {
                "chain": row["chain"],
                "sku": None,
                "state": None,
            },
            "period": {
                "start": str(row["month_year"]),
                "end": None,
            },
            "source": "skuba",
            "status": "inferred",
            "evidence": {
                "buying_stores_before": int(row["buying_stores_prior"]),
                "buying_stores_after": int(row["buying_stores"]),
                "stores_added": int(row["stores_added"]),
            },
        })

    return records