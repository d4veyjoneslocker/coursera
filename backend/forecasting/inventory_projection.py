import pandas as pd

def _evidence_window_end(
    as_of_date,
    floor_date,
    status,
    recommendation_event,
    current_path_inbounds,
    floor_cases,
    current_cases,
    velocity_cases_per_week,
    min_days=14,
    tail_days=5,
):
    as_of_date = pd.Timestamp(as_of_date).normalize()

    # 1. Action: show the recommended order landing and restoring the floor.
    if recommendation_event is not None:
        rec_delivery = pd.Timestamp(
            recommendation_event["expected_delivery_date"]
        ).normalize()
        end = rec_delivery + pd.Timedelta(days=tail_days)
        return max(end, as_of_date + pd.Timedelta(days=min_days))

    # 2. Monitor/covered: end at the FIRST inbound that lifts inventory back
    #    above the floor -- that's the order doing the covering. Ignore the rest.
    inv = float(current_cases)
    cursor = as_of_date
    for event in current_path_inbounds:  # already sorted by date
        event_date = pd.Timestamp(event["date"]).normalize()

        # draw down to this event
        weeks = max((event_date - cursor).days, 0) / 7
        inv = max(inv - velocity_cases_per_week * weeks, 0)
        inv += float(event["cases"])
        cursor = event_date

        if inv >= floor_cases:
            end = event_date + pd.Timedelta(days=tail_days)
            return max(end, as_of_date + pd.Timedelta(days=min_days))

    # 3. Healthy / approaching floor / nothing covers: show through the point
    #    we're provably safe (floor crossing), or the min window.
    if pd.notna(floor_date):
        end = pd.Timestamp(floor_date).normalize() + pd.Timedelta(days=tail_days)
        return max(end, as_of_date + pd.Timedelta(days=min_days))

    return as_of_date + pd.Timedelta(days=min_days)

def project_inventory_trajectory(
    *,
    start_date,
    start_inventory_cases: float,
    velocity_cases_per_week: float,
    supply_events: list[dict] | pd.DataFrame | None = None,
    end_date=None,
    lookahead_days: int = 42,
) -> pd.DataFrame:
    """
    Project daily inventory from a starting inventory position.

    This is a pure forecasting function.

    It does NOT know:
    - whether supply is a confirmed PO
    - whether supply is a projected order
    - whether supply is a SKUba recommendation
    - whether a PO should be expedited
    - whether inventory is healthy
    - what the floor / buffer / target is

    It only knows:
        starting inventory
        - daily consumption
        + supply arriving on specific dates

    Expected supply event shape:
        {
            "receipt_date": <date>,
            "cases": <float>,
        }

    Returns one row per day:
        date
        inventory_cases
        weeks_on_hand
        inbound_cases
    """

    start_date = pd.Timestamp(
        start_date
    ).normalize()

    if end_date is None:
        end_date = (
            start_date
            + pd.Timedelta(
                days=lookahead_days
            )
        )
    else:
        end_date = pd.Timestamp(
            end_date
        ).normalize()

    start_inventory_cases = float(
        start_inventory_cases
    )

    velocity_cases_per_week = float(
        velocity_cases_per_week
    )

    if velocity_cases_per_week <= 0:
        raise ValueError(
            "Cannot project inventory without positive velocity."
        )

    daily_velocity = (
        velocity_cases_per_week / 7
    )

    # ---------------------------------------------------------
    # Normalize supply events
    # ---------------------------------------------------------

    if supply_events is None:
        events = pd.DataFrame(
            columns=[
                "receipt_date",
                "cases",
            ]
        )

    elif isinstance(
        supply_events,
        pd.DataFrame,
    ):
        events = supply_events.copy()

    else:
        events = pd.DataFrame(
            supply_events
        )

    if events.empty:
        inbound_by_date = {}

    else:
        if "receipt_date" not in events.columns:
            raise ValueError(
                "Supply events must contain receipt_date."
            )

        if "cases" not in events.columns:
            raise ValueError(
                "Supply events must contain cases."
            )

        events["receipt_date"] = (
            pd.to_datetime(
                events["receipt_date"],
                errors="coerce",
            ).dt.normalize()
        )

        events["cases"] = pd.to_numeric(
            events["cases"],
            errors="coerce",
        )

        events = events[
            events["receipt_date"].notna()
            & events["cases"].notna()
            & (events["cases"] > 0)
        ].copy()

        inbound_by_date = (
            events.groupby(
                "receipt_date"
            )["cases"]
            .sum()
            .to_dict()
        )

    # ---------------------------------------------------------
    # Project
    # ---------------------------------------------------------

    inventory_cases = (
        start_inventory_cases
    )

    rows = []

    for date in pd.date_range(
        start_date,
        end_date,
        freq="D",
    ):
        # Starting inventory represents inventory
        # at the beginning of start_date.
        #
        # Consume one day's demand before each
        # subsequent day's inventory position.
        if date != start_date:
            inventory_cases = max(
                inventory_cases
                - daily_velocity,
                0.0,
            )

        inbound_cases = float(
            inbound_by_date.get(
                date,
                0.0,
            )
        )

        inventory_cases += (
            inbound_cases
        )

        weeks_on_hand = (
            inventory_cases
            / velocity_cases_per_week
        )

        rows.append(
            {
                "date": date,
                "inventory_cases": float(
                    inventory_cases
                ),
                "weeks_on_hand": float(
                    weeks_on_hand
                ),
                "inbound_cases": (
                    inbound_cases
                ),
            }
        )

    return pd.DataFrame(rows)