import pandas as pd
import numpy as np
from pathlib import Path


def build_month_multipliers(months, rng):
    n = len(months)
    total_growth = rng.uniform(1.45, 1.85)
    log_drift = np.log(total_growth) / (n - 1)
    log_noise = rng.normal(0, 0.10, size=n)
    log_path = np.cumsum(np.full(n, log_drift) + log_noise)
    log_path -= log_path[0]
    trend = np.exp(log_path)

    for _ in range(rng.integers(2, 5)):
        idx = rng.integers(1, n)
        direction = rng.choice([-1, 1])
        magnitude = rng.uniform(0.10, 0.25)
        trend[idx] *= 1 + direction * magnitude

    seasonal = np.array([
        0.88 if m.month in (1, 2) else
        1.06 if m.month in (10, 11) else
        1.0
        for m in months
    ])

    return {m: float(trend[i] * seasonal[i]) for i, m in enumerate(months)}


def apply_demo_insight_patterns(df, stores, months, rng):
    df = df.copy()

    current_month = months[-1]
    completed_months = [m for m in months if m < current_month]
    latest_completed_3 = completed_months[-3:]
    prior_completed_3 = completed_months[-6:-3]
    detection_months = months[-3:]

    def upsert(store_id, sku, month, units):
        nonlocal df

        month_str = str(month)
        mask = (
            (df["coded_customer"] == store_id)
            & (df["sku"] == sku)
            & (df["month_year"].astype(str) == month_str)
        )

        if mask.any():
            df.loc[mask, "units"] = int(units)
            df.loc[mask, "revenue"] = round(int(units) * 5.49, 2)
        else:
            store = stores[stores["coded_customer"] == store_id].iloc[0]

            new_row = {
                "month_year": month_str,
                "coded_customer": store_id,
                "store_name": store["store_name"],
                "chain": store["chain"],
                "channel": store["channel"],
                "distributor": store["distributor"],
                "dc": store["dc"],
                "sku": sku,
                "units": int(units),
                "revenue": round(int(units) * 5.49, 2),
                "state": store["state"],
                "city": store["city"],
                "zip": store["zip"],
                "customer_name": store["store_name"],
                "store_number": store_id,
                "street_address": store["street_address"],
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Velocity gap: SKU C performs much better in Whole Foods than Sprouts
    sku = "SKU C"
    wf = stores[stores["chain"] == "Whole Foods"]["coded_customer"].head(45)
    sprouts = stores[stores["chain"] == "Sprouts"]["coded_customer"].head(45)

    for s in wf:
        for m in latest_completed_3:
            upsert(s, sku, m, int(rng.normal(30, 5)))

    for s in sprouts:
        for m in latest_completed_3:
            upsert(s, sku, m, int(max(2, rng.normal(9, 2))))

    # Void opportunity: SKU E missing from many Whole Foods stores
    sku = "SKU E"
    wf_all = stores[stores["chain"] == "Whole Foods"]["coded_customer"].head(100)

    carrying = wf_all[:25]
    voids = wf_all[25:75]
    new_carry = wf_all[75:85]

    for s in carrying:
        for m in latest_completed_3:
            upsert(s, sku, m, int(rng.normal(38, 6)))

    for s in new_carry:
        upsert(s, sku, current_month, int(rng.normal(7, 2)))

    anchor = "SKU A"
    for s in voids:
        # remove SKU E from detection window, but make sure store is active
        df = df[
            ~(
                (df["coded_customer"] == s)
                & (df["sku"] == sku)
                & (df["month_year"].astype(str).isin([str(m) for m in detection_months]))
            )
        ]

        for m in detection_months:
            upsert(s, anchor, m, int(rng.normal(13, 3)))

    # SKU velocity improvement: SKU B improves in recent 3 months
    sku = "SKU B"
    sample = stores[stores["chain"].isin(["Kroger", "Target", "Whole Foods"])]["coded_customer"].head(140)

    for s in sample:
        for m in prior_completed_3:
            upsert(s, sku, m, int(max(2, rng.normal(7, 2))))
        for m in latest_completed_3:
            upsert(s, sku, m, int(rng.normal(19, 4)))

    # Chain growth: Target grows strongly vs prior 3 months
    growth_sku = "SKU A"
    target_stores = stores[stores["chain"] == "Target"]["coded_customer"].head(120)

    for s in target_stores:
        for m in prior_completed_3:
            upsert(s, growth_sku, m, int(max(1, rng.normal(5, 1))))
        for m in latest_completed_3:
            upsert(s, growth_sku, m, int(rng.normal(32, 5)))

    return df


def generate_dummy_cpg_data(seed=42, output_dir="backend/demo/demo_data"):
    rng = np.random.default_rng(seed)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    months = pd.period_range(
        end=pd.Timestamp.today().to_period("M"),
        periods=14,
        freq="M",
    )

    skus = ["SKU A", "SKU B", "SKU C", "SKU D", "SKU E"]

    retailers = [
        ("Whole Foods", "Natural", 0.13, 1.22),
        ("Sprouts", "Natural", 0.10, 1.05),
        ("Natural Grocers", "Natural", 0.07, 0.95),
        ("Fresh Thyme", "Natural", 0.05, 0.92),
        ("MOM's Organic Market", "Natural", 0.03, 1.08),
        ("The Fresh Market", "Grocery", 0.06, 1.03),
        ("Kroger", "Grocery", 0.08, 0.88),
        ("Albertsons", "Grocery", 0.06, 0.84),
        ("Publix", "Grocery", 0.06, 0.90),
        ("Wegmans", "Grocery", 0.04, 1.12),
        ("H-E-B", "Grocery", 0.04, 1.00),
        ("Target", "Mass", 0.05, 0.78),
        ("Walmart", "Mass", 0.04, 0.72),
        ("Thrive Market", "E-Commerce", 0.03, 1.45),
        ("GoPuff", "E-Commerce", 0.03, 1.55),
        ("Delta", "Alternative", 0.02, 1.20),
        ("Foxtrot", "Alternative", 0.02, 1.08),
        ("Independent", "Specialty", 0.11, 0.78),
        ("Regional Grocery", "Grocery", 0.08, 0.80),
    ]

    retailer_names = [r[0] for r in retailers]
    retailer_probs = np.array([r[2] for r in retailers], dtype=float)
    retailer_probs = retailer_probs / retailer_probs.sum()

    channel_by_chain = {r[0]: r[1] for r in retailers}
    velocity_by_chain = {r[0]: r[3] for r in retailers}

    states = ["CA", "TX", "FL", "NY", "IL", "CO", "WA", "OR", "AZ", "NC", "GA", "MA"]
    cities_by_state = {
        "CA": ["Los Angeles", "San Diego", "San Francisco", "Oakland"],
        "TX": ["Austin", "Dallas", "Houston"],
        "FL": ["Miami", "Tampa", "Orlando"],
        "NY": ["New York", "Brooklyn", "Buffalo"],
        "IL": ["Chicago", "Evanston"],
        "CO": ["Denver", "Boulder"],
        "WA": ["Seattle", "Bellevue"],
        "OR": ["Portland", "Bend"],
        "AZ": ["Phoenix", "Scottsdale"],
        "NC": ["Charlotte", "Raleigh"],
        "GA": ["Atlanta", "Savannah"],
        "MA": ["Boston", "Cambridge"],
    }

    behaviors = ["healthy", "struggling", "inactive", "revived", "new", "sporadic"]
    behavior_probs = [0.40, 0.22, 0.10, 0.08, 0.08, 0.12]

    store_rows = []

    for i in range(1200):
        chain = rng.choice(retailer_names, p=retailer_probs)
        distributor = rng.choice(["UNFI", "KeHE"], p=[0.68, 0.32])

        state = rng.choice(states)
        city = rng.choice(cities_by_state[state])

        behavior = rng.choice(behaviors, p=behavior_probs)

        start_idx = int(rng.integers(0, 8))
        if behavior == "new":
            start_idx = int(rng.integers(10, 13))

        base_velocity = max(4.5, rng.normal(11.0, 2.6)) * velocity_by_chain[chain]

        store_rows.append({
            "coded_customer": f"S{i + 1:05d}",
            "store_name": f"{chain} #{rng.integers(100, 9999)}",
            "chain": chain,
            "channel": channel_by_chain[chain],
            "distributor": distributor,
            "dc": rng.choice(["DC West", "DC Central", "DC East", "DC South"]),
            "state": state,
            "city": city,
            "zip": f"{rng.integers(10000, 99999)}",
            "street_address": f"{rng.integers(100, 9999)} Main St",
            "base_velocity": base_velocity,
            "start_idx": start_idx,
            "behavior": behavior,
            "store_quality": rng.normal(1.0, 0.20),
            "skip_prob": rng.uniform(0.10, 0.30),
        })

    stores = pd.DataFrame(store_rows)

    month_multipliers = build_month_multipliers(months, rng)
    sku_profiles = {sku: rng.uniform(0.80, 1.25) for sku in skus}

    purchase_prob_by_behavior = {
        "healthy": 0.58,
        "struggling": 0.34,
        "inactive": 0.42,
        "revived": 0.38,
        "new": 0.46,
        "sporadic": 0.22,
    }

    rows = []

    for _, store in stores.iterrows():
        store_scalar = store["store_quality"]

        for month_idx, month in enumerate(months):
            if month_idx < store["start_idx"]:
                continue

            # lifecycle patterns
            if store["behavior"] == "inactive" and month_idx >= len(months) - 4:
                continue

            if store["behavior"] == "revived" and len(months) - 7 <= month_idx <= len(months) - 4:
                continue

            months_since_start = max(0, month_idx - store["start_idx"])

            if store["behavior"] == "struggling":
                behavior_multiplier = max(0.18, 1 - 0.085 * months_since_start)
            elif store["behavior"] == "revived" and month_idx >= len(months) - 3:
                behavior_multiplier = 1.25
            elif store["behavior"] == "new":
                behavior_multiplier = 0.85 + 0.08 * months_since_start
            else:
                behavior_multiplier = 1.0

            skip_prob = (
                0.48 if store["behavior"] == "sporadic"
                else 0.30 if store["behavior"] == "struggling"
                else store["skip_prob"]
            )

            if rng.random() < skip_prob:
                continue

            month_scalar = month_multipliers[month]

            for sku in skus:
                # SKU-level purchase gaps
                base_purchase_prob = purchase_prob_by_behavior[store["behavior"]]

                if sku == "SKU E":
                    base_purchase_prob *= 0.45
                elif sku == "SKU D":
                    base_purchase_prob *= 0.55
                elif sku == "SKU A":
                    base_purchase_prob *= 1.15

                if rng.random() > min(base_purchase_prob, 0.82):
                    continue

                sku_scalar = sku_profiles[sku]

                noise = rng.normal(1.0, 0.24)
                if rng.random() < 0.10:
                    noise *= rng.uniform(0.45, 1.70)

                base = (
                    store["base_velocity"]
                    * store_scalar
                    * month_scalar
                    * sku_scalar
                    * behavior_multiplier
                    * noise
                )

                units = int(max(1, rng.normal(base, max(1, base * 0.32))))
                revenue = round(units * 5.49, 2)

                rows.append({
                    "month_year": str(month),
                    "coded_customer": store["coded_customer"],
                    "store_name": store["store_name"],
                    "customer_name": store["store_name"],
                    "store_number": store["coded_customer"],
                    "street_address": store["street_address"],
                    "chain": store["chain"],
                    "channel": store["channel"],
                    "distributor": store["distributor"],
                    "dc": store["dc"],
                    "sku": sku,
                    "units": units,
                    "revenue": revenue,
                    "state": store["state"],
                    "city": store["city"],
                    "zip": store["zip"],
                })

    df = pd.DataFrame(rows)

    df = apply_demo_insight_patterns(df=df, stores=stores, months=months, rng=rng)

    df["upc"] = (
        df["sku"]
        .astype("category")
        .cat.codes
        .astype(str)
        .str.zfill(12)
    )

    df["month_year"] = pd.PeriodIndex(df["month_year"], freq="M")
    df["year"] = df["month_year"].dt.year
    df["month"] = df["month_year"].dt.month

    df["helper"] = (
        df["coded_customer"].astype(str)
        + "_"
        + df["month_year"].astype(str)
        + "_"
        + df["sku"].astype(str)
    )

    df["pod_helper"] = (
        df["coded_customer"].astype(str)
        + "_"
        + df["sku"].astype(str)
    )

    df["month_year"] = df["month_year"].astype(str)
    df["units"] = df["units"].astype(int)

    df = df.sort_values(
        ["month_year", "distributor", "chain", "coded_customer", "sku"]
    ).reset_index(drop=True)

    df.to_csv(out_dir / "demo_combined.csv", index=False)

    print(f"Saved to: {out_dir / 'demo_combined.csv'}")
    print(f"Rows: {len(df):,}")
    print(f"Buying stores: {df['coded_customer'].nunique():,}")
    print(f"Chains: {df['chain'].nunique():,}")
    print(f"Channels: {df['channel'].nunique():,}")
    print(f"Months: {df['month_year'].min()} to {df['month_year'].max()}")
    print()
    print("Behavior mix:")
    print(stores["behavior"].value_counts().to_string())
    print()
    print("Channel mix:")
    print(stores["channel"].value_counts().to_string())

    return df


if __name__ == "__main__":
    generate_dummy_cpg_data()