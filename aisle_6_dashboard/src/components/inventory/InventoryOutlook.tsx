"use client"

import { useMemo } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

type Theme = {
  surface: string
  line: string
  accent_color: string
  charcoal: string
}

type TrajectoryPoint = {
  date: string
  inventory_cases: number
  weeks_on_hand: number
}

type ConfirmedPoEvent = {
  receipt_date: string | null
  expected_delivery_date: string | null
  cases: number
  po_status: string
  is_stale: boolean
  overdue_days: number
  timing_source: string | null
  timing_flag: string | null
}

type Intervention = {
  intervention_required: boolean
  intervention_type: string
  recommended_cases: number
  needed_by_date?: string | null
  order_by_date?: string | null
  surface_date?: string | null
  planned_order_date?: string | null
  expected_delivery_date?: string | null
  reason?: string | null
}

type ProjectedOrderEvaluation = {
  exists?: boolean
  resolves_breach?: boolean
  reason?: string | null
  resolving_order?: {
    cases?: number
    order_date?: string | null
    expected_delivery_date?: string | null
    source?: string | null
  } | null
}

type Breach = {
  start_date: string
  end_date: string
  lowest_woh: number
  lowest_woh_date: string
  breaches_tolerance: boolean
  first_tolerance_breach_date: string | null
  first_oos_date: string | null
  projected_order?: ProjectedOrderEvaluation
  intervention?: Intervention
}

export type InventoryAssessment = {
  distributor: string
  dc: string
  sku: string
  product_name: string

  assessment_status: string
  inventory_status: string
  projection_available: boolean
  projection_unavailable_reason: string | null

  as_of_date?: string | null
  report_date: string | null

  observed_quantity_on_hand_cases: number | null
  estimated_quantity_on_hand_cases?: number | null
  estimated_weeks_on_hand?: number | null
  quantity_on_po_cases: number | null

  units_per_case: number | null
  units_per_week?: number | null
  cases_per_week?: number | null

  planning_lead_time_days: number | null
  planning_lead_time_source: string | null

  summary: {
    status: string
    intervention_types: string[]
    active_intervention_types: string[]
    recommended_cases: number
    has_active_action: boolean
    has_review: boolean
    has_expedite: boolean
    has_new_order: boolean
    monitor_projected_order: boolean
    future_replenishment: boolean
    has_floor_breach: boolean | null
    has_material_breach: boolean | null
  }

  narrative: string

  baseline: {
    as_of_date: string
    report_date: string
    observed_cases: number
    estimated_cases_today: number
    velocity_cases_per_week: number
    confirmed_po_events: ConfirmedPoEvent[]
    trajectory: TrajectoryPoint[]
  } | null

  skuba_trajectory?: TrajectoryPoint[]

  breaches: Breach[]
}

type SupplyEvent = {
  id: string
  kind: "confirmed" | "projected" | "skuba"
  cases: number
  date: string | null
  label: string
  secondary: string | null
  status?: string | null
  inventoryOnDelivery?: number | null
  weeksOnHandOnDelivery?: number | null
}

function formatDate(
  date: string | null | undefined
) {
  if (!date) return "—"

  return new Date(
    `${date}T00:00:00`
  ).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

function formatCases(
  value: number | null | undefined
) {
  if (value == null) return "—"

  return Math.round(
    value
  ).toLocaleString()
}

function formatOneDecimal(
  value: number | null | undefined
) {
  if (value == null) return "—"

  return value.toLocaleString(
    undefined,
    {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }
  )
}

function dateValue(
  date: string | null | undefined
) {
  if (!date) return Number.POSITIVE_INFINITY

  return new Date(
    `${date}T00:00:00`
  ).getTime()
}

function getInventoryAtDate(
  trajectory: TrajectoryPoint[],
  date: string | null | undefined
) {
  if (!date) return null

  const exact = trajectory.find(
    (point) => point.date === date
  )

  if (exact) {
    return exact
  }

  const target = dateValue(date)

  const next = trajectory.find(
    (point) =>
      dateValue(point.date) >= target
  )

  return next ?? null
}

function getPrimaryNewOrder(
  breaches: Breach[]
) {
  return breaches
    .map(
      (breach) => breach.intervention
    )
    .filter(
      (
        intervention
      ): intervention is Intervention =>
        Boolean(intervention)
    )
    .find(
      (intervention) =>
        intervention.intervention_type ===
          "new_order" &&
        intervention.recommended_cases > 0
    )
}

function getPrimaryExpedite(
  breaches: Breach[]
) {
  return breaches
    .map(
      (breach) => breach.intervention
    )
    .filter(
      (
        intervention
      ): intervention is Intervention =>
        Boolean(intervention)
    )
    .find(
      (intervention) =>
        intervention.intervention_type ===
        "expedite_po"
    )
}

function InventoryBlocks({
  cases,
  accentColor,
}: {
  cases: number
  accentColor: string
}) {
  /*
   * Visual only.
   *
   * We intentionally scale the blocks rather than drawing
   * one block per case.
   */
  const targetBlocks = 8

  const scale =
    cases > 0
      ? Math.max(
          1,
          Math.ceil(cases / targetBlocks)
        )
      : 1

  const fullBlocks = Math.floor(
    cases / scale
  )

  const remainder =
    cases - fullBlocks * scale

  const blockCount = Math.min(
    targetBlocks,
    fullBlocks +
      (remainder > 0 ? 1 : 0)
  )

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {Array.from({
        length: blockCount,
      }).map((_, index) => {
        const partial =
          index === blockCount - 1 &&
          remainder > 0

        return (
          <div
            key={index}
            className="h-7 w-7 rounded-[7px]"
            style={{
              backgroundColor:
                accentColor,
              opacity: partial
                ? Math.max(
                    0.3,
                    remainder / scale
                  )
                : 1,
              boxShadow:
                "inset 0 -2px 0 rgba(0,0,0,0.06)",
            }}
          />
        )
      })}
    </div>
  )
}

function InventoryVelocityVisual({
  data,
  accentColor,
  theme,
}: {
  data: InventoryAssessment
  accentColor: string
  theme: Theme
}) {
  const onHand =
    data.estimated_quantity_on_hand_cases ??
    data.baseline?.estimated_cases_today ??
    0

  const velocity =
    data.cases_per_week ??
    data.baseline
      ?.velocity_cases_per_week ??
    0

  return (
    <div
      className="rounded-[20px] border p-5"
      style={{
        background: "#FCFAF6",
        borderColor: "#EEE5D8",
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div
            className="text-[11px] font-semibold uppercase tracking-[0.13em]"
            style={{
              color: theme.accent_color,
            }}
          >
            Inventory at the DC
          </div>

          <div
            className="mt-1 text-sm"
            style={{
              color: "#8A8378",
            }}
          >
            Current inventory relative to
            weekly sell-through
          </div>
        </div>

        {data.estimated_weeks_on_hand !=
          null && (
          <div className="shrink-0 text-right">
            <div
              className="text-2xl font-semibold"
              style={{
                color: theme.charcoal,
              }}
            >
              {formatOneDecimal(
                data.estimated_weeks_on_hand
              )}
            </div>

            <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[#8A8378]">
              WOH
            </div>
          </div>
        )}
      </div>

      <div className="mt-5 grid items-center gap-5 md:grid-cols-[1fr_auto_1fr]">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8A8378]">
            Estimated on hand
          </div>

          <InventoryBlocks
            cases={onHand}
            accentColor={accentColor}
          />

          <div
            className="mt-3 text-xl font-semibold"
            style={{
              color: theme.charcoal,
            }}
          >
            {formatCases(onHand)} cases
          </div>

          <div className="mt-0.5 text-xs text-[#8A8378]">
            at the DC today
          </div>
        </div>

        <div className="hidden min-w-[72px] text-center md:block">
          <div
            className="text-2xl"
            style={{
              color: theme.accent_color,
            }}
          >
            →
          </div>

          <div className="mt-1 text-[9px] font-semibold uppercase tracking-[0.12em] text-[#9A9389]">
            Weekly
            <br />
            sell-through
          </div>
        </div>

        <div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8A8378]">
            Weekly velocity
          </div>

          <InventoryBlocks
            cases={velocity}
            accentColor={
              theme.charcoal
            }
          />

          <div
            className="mt-3 text-xl font-semibold"
            style={{
              color: theme.charcoal,
            }}
          >
            {formatOneDecimal(
              velocity
            )}{" "}
            cases
          </div>

          <div className="mt-0.5 text-xs text-[#8A8378]">
            leave each week
          </div>
        </div>
      </div>

      {velocity > 0 && (
        <div className="mt-5 border-t border-[#EEE8DF] pt-4 text-xs leading-5 text-[#8A8378]">
          <span
            className="font-semibold"
            style={{
              color: theme.charcoal,
            }}
          >
            About{" "}
            {formatOneDecimal(
              onHand / velocity
            )}{" "}
            weeks of inventory
          </span>{" "}
          is currently sitting at the DC
          at the recent sales rate.
        </div>
      )}
    </div>
  )
}

function OutlookTooltip({
  active,
  payload,
  label,
  floorCases,
  confirmedEvents,
  skubaOrder,
  baselineTrajectory,
  skubaTrajectory,
}: any) {
  if (!active || !payload?.length) {
    return null
  }

  const baseline = payload.find(
    (item: any) =>
      item.dataKey ===
      "inventory_cases"
  )

  const skuba = payload.find(
    (item: any) =>
      item.dataKey ===
      "skuba_inventory_cases"
  )

  const confirmed =
    confirmedEvents.find(
      (event: ConfirmedPoEvent) =>
        (event.receipt_date ??
          event.expected_delivery_date) ===
        label
    )

  const isSkubaDelivery =
    skubaOrder?.expected_delivery_date ===
    label

  const baselinePoint =
    getInventoryAtDate(
      baselineTrajectory,
      label
    )

  const skubaPoint =
    getInventoryAtDate(
      skubaTrajectory,
      label
    )

  return (
    <div className="min-w-[220px] rounded-xl border border-[#E5DDD0] bg-[#FFFEFB] px-3.5 py-3 shadow-sm">
      <div className="mb-2 text-xs font-medium text-[#8A8378]">
        {formatDate(label)}
      </div>

      {confirmed && (
        <div className="mb-3 rounded-lg bg-[#FBF6EF] px-3 py-2">
          <div className="text-xs font-semibold text-[#343332]">
            +{formatCases(
              confirmed.cases
            )}{" "}
            confirmed cases
          </div>

          {baselinePoint && (
            <div className="mt-1 text-[11px] leading-5 text-[#705C4F]">
              {formatCases(
                baselinePoint.inventory_cases
              )}{" "}
              cases on hand upon delivery
              {" · "}
              {formatOneDecimal(
                baselinePoint.weeks_on_hand
              )}{" "}
              WOH
            </div>
          )}
        </div>
      )}

      {isSkubaDelivery && (
        <div className="mb-3 rounded-lg bg-[#F4F2EE] px-3 py-2">
          <div className="text-xs font-semibold text-[#343332]">
            +{formatCases(
              skubaOrder.recommended_cases
            )}{" "}
            SKUba-recommended cases
          </div>

          {skubaPoint && (
            <div className="mt-1 text-[11px] leading-5 text-[#705C4F]">
              {formatCases(
                skubaPoint.inventory_cases
              )}{" "}
              cases on hand upon delivery
              {" · "}
              {formatOneDecimal(
                skubaPoint.weeks_on_hand
              )}{" "}
              WOH
            </div>
          )}
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-6">
          <span className="text-sm text-[#6F685F]">
            Confirmed supply
          </span>

          <span className="text-sm font-semibold text-[#26231F]">
            {formatCases(
              Number(
                baseline?.value ?? 0
              )
            )}{" "}
            cases
          </span>
        </div>

        {skuba && (
          <div className="flex items-center justify-between gap-6">
            <span className="text-sm text-[#6F685F]">
              With SKUba
            </span>

            <span className="text-sm font-semibold text-[#26231F]">
              {formatCases(
                Number(
                  skuba.value ?? 0
                )
              )}{" "}
              cases
            </span>
          </div>
        )}
      </div>

      <div className="mt-2.5 border-t border-[#EEE8DF] pt-2 text-xs text-[#8A8378]">
        3 WOH floor:{" "}
        {formatCases(floorCases)} cases
      </div>
    </div>
  )
}

function SupplyTimeline({
  data,
  events,
  accentColor,
  theme,
}: {
  data: InventoryAssessment
  events: SupplyEvent[]
  accentColor: string
  theme: Theme
}) {
  const start =
    data.as_of_date ??
    data.baseline?.as_of_date

  const datedEvents = events
    .filter(
      (event) =>
        event.date &&
        dateValue(event.date) >=
          dateValue(start)
    )
    .sort(
      (a, b) =>
        dateValue(a.date) -
        dateValue(b.date)
    )
    .slice(0, 3)

  const allDates = [
    start,
    ...datedEvents.map(
      (event) => event.date
    ),
  ].filter(Boolean) as string[]

  if (!start || !allDates.length) {
    return null
  }

  const minDate = dateValue(start)

  const maxDate = Math.max(
    ...allDates.map(dateValue),
    minDate + 86400000
  )

  function position(
    date: string
  ) {
    if (maxDate === minDate) {
      return 0
    }

    const raw =
      ((dateValue(date) - minDate) /
        (maxDate - minDate)) *
      100

    return Math.max(
      0,
      Math.min(100, raw)
    )
  }

  return (
    <div
      className="mb-4 rounded-[18px] border px-4 pb-5 pt-4"
      style={{
        borderColor: "#EEE5D8",
        background: "#FCFAF6",
      }}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="text-xs font-semibold text-[#343332]">
          Supply timeline
        </div>

        <div className="text-[10px] text-[#8A8378]">
          Confirmed, projected, and
          SKUba supply
        </div>
      </div>

      <div className="relative mt-6 h-[66px]">
        <div className="absolute left-[2%] right-[2%] top-[11px] h-[2px] bg-[#E8DFD5]" />

        <div
          className="absolute top-[5px]"
          style={{
            left: "2%",
          }}
        >
          <div
            className="h-3.5 w-3.5 -translate-x-1/2 rounded-full border-[3px] bg-white"
            style={{
              borderColor:
                accentColor,
            }}
          />

          <div className="mt-2 -translate-x-1/2 whitespace-nowrap text-center">
            <div className="text-[10px] font-semibold text-[#343332]">
              Today
            </div>

            <div className="text-[9px] text-[#8A8378]">
              {formatDate(start)}
            </div>
          </div>
        </div>

        {datedEvents.map(
          (event, index) => {
            const left =
              2 +
              position(
                event.date as string
              ) *
                0.96

            const eventColor =
              event.kind === "skuba"
                ? theme.charcoal
                : event.kind ===
                    "projected"
                  ? "#C9A96E"
                  : accentColor

            return (
              <div
                key={event.id}
                className="absolute top-[5px]"
                style={{
                  left: `${left}%`,
                  zIndex:
                    datedEvents.length -
                    index,
                }}
              >
                <div
                  className={`h-3.5 w-3.5 -translate-x-1/2 rounded-full border-[3px] bg-white ${
                    event.kind ===
                    "projected"
                      ? "border-dashed"
                      : ""
                  }`}
                  style={{
                    borderColor:
                      eventColor,
                  }}
                />

                <div className="mt-2 -translate-x-1/2 whitespace-nowrap text-center">
                  <div className="text-[10px] font-semibold text-[#343332]">
                    +
                    {formatCases(
                      event.cases
                    )}{" "}
                    {event.kind ===
                    "confirmed"
                      ? "confirmed"
                      : event.kind ===
                          "projected"
                        ? "projected"
                        : "SKUba"}
                  </div>

                  <div className="text-[9px] text-[#8A8378]">
                    {formatDate(
                      event.date
                    )}
                  </div>
                </div>
              </div>
            )
          }
        )}
      </div>
    </div>
  )
}

function SupplyEventRow({
  event,
  accentColor,
  theme,
}: {
  event: SupplyEvent
  accentColor: string
  theme: Theme
}) {
  const projected =
    event.kind === "projected"

  const skuba =
    event.kind === "skuba"

  const markerColor = skuba
    ? theme.charcoal
    : projected
      ? "#C9A96E"
      : accentColor

  return (
    <div className="flex items-start gap-3 rounded-xl px-2 py-2.5 transition hover:bg-[#F8F3ED]">
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border bg-white text-[10px] font-semibold ${
          projected
            ? "border-dashed"
            : ""
        }`}
        style={{
          borderColor: markerColor,
          color: markerColor,
        }}
      >
        +
        {formatCases(
          event.cases
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="text-xs font-semibold text-[#343332]">
            {event.label}
          </div>

          {event.status && (
            <div
              className="shrink-0 text-[9px] font-semibold uppercase tracking-[0.08em]"
              style={{
                color:
                  event.status ===
                  "Too late"
                    ? "#B94A30"
                    : event.status ===
                        "Confirmed"
                      ? "#55735E"
                      : theme.charcoal,
              }}
            >
              {event.status}
            </div>
          )}
        </div>

        {event.date && (
          <div className="mt-0.5 text-[11px] text-[#8A8378]">
            {event.kind ===
            "projected"
              ? "Est. receipt "
              : event.kind ===
                  "skuba"
                ? "Modeled receipt "
                : "Expected "}
            {formatDate(
              event.date
            )}
          </div>
        )}

        {event.secondary && (
          <div className="mt-1 text-[10px] leading-4 text-[#705C4F]">
            {event.secondary}
          </div>
        )}
      </div>
    </div>
  )
}

function SupplyRail({
  confirmedEvents,
  projectedEvents,
  skubaEvent,
  accentColor,
  theme,
}: {
  confirmedEvents: SupplyEvent[]
  projectedEvents: SupplyEvent[]
  skubaEvent: SupplyEvent | null
  accentColor: string
  theme: Theme
}) {
  const visibleProjected =
    projectedEvents.slice(0, 2)

  const remainingProjected =
    Math.max(
      0,
      projectedEvents.length -
        visibleProjected.length
    )

  return (
    <aside className="min-w-0 border-t border-[#EEE8DF] pt-5 lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div
          className="text-[11px] font-semibold uppercase tracking-[0.13em]"
          style={{
            color: theme.accent_color,
          }}
        >
          Supply / POs
        </div>

        <div className="text-[10px] text-[#9A9389]">
          Next events
        </div>
      </div>

      <div className="space-y-1">
        {confirmedEvents.length >
          0 ? (
          confirmedEvents.map(
            (event) => (
              <SupplyEventRow
                key={event.id}
                event={event}
                accentColor={
                  accentColor
                }
                theme={theme}
              />
            )
          )
        ) : (
          <div className="px-2 py-3 text-xs text-[#8A8378]">
            No confirmed inbound.
          </div>
        )}

        {visibleProjected.map(
          (event) => (
            <SupplyEventRow
              key={event.id}
              event={event}
              accentColor={
                accentColor
              }
              theme={theme}
            />
          )
        )}

        {remainingProjected > 0 && (
          <div className="px-3 py-2 text-[10px] text-[#8A8378]">
            +
            {remainingProjected} later
            distributor{" "}
            {remainingProjected === 1
              ? "projection"
              : "projections"}
          </div>
        )}
      </div>

      {skubaEvent && (
        <>
          <div className="my-4 border-t border-[#EEE8DF]" />

          <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8A8378]">
            SKUba
          </div>

          <SupplyEventRow
            event={skubaEvent}
            accentColor={accentColor}
            theme={theme}
          />
        </>
      )}
    </aside>
  )
}

export function InventoryOutlook({
  data,
  accentColor,
  theme,
}: {
  data: InventoryAssessment
  accentColor: string
  theme: Theme
}) {
  if (
    !data.projection_available ||
    !data.baseline
  ) {
    return (
      <div className="rounded-[20px] border border-[#DED8E8] bg-[#F5F2FA] p-5">
        <div className="text-sm font-semibold text-[#343332]">
          Projection unavailable
        </div>

        <div className="mt-1 text-sm leading-6 text-[#705C4F]">
          {data.narrative ||
            data.projection_unavailable_reason ||
            "SKUba cannot calculate a forward inventory projection for this SKU."}
        </div>
      </div>
    )
  }

  const baselineTrajectory =
    data.baseline.trajectory ?? []

  const skubaTrajectory =
    data.skuba_trajectory ?? []

  if (!baselineTrajectory.length) {
    return null
  }

  /*
   * IMPORTANT:
   * We join by DATE here rather than
   * assuming both arrays always have the
   * exact same index alignment.
   */
  const skubaByDate = new Map(
    skubaTrajectory.map(
      (point) => [
        point.date,
        point,
      ]
    )
  )

  const series =
    baselineTrajectory.map(
      (point) => ({
        date: point.date,
        inventory_cases:
          point.inventory_cases,
        weeks_on_hand:
          point.weeks_on_hand,
        skuba_inventory_cases:
          skubaByDate.get(
            point.date
          )?.inventory_cases ??
          null,
        skuba_weeks_on_hand:
          skubaByDate.get(
            point.date
          )?.weeks_on_hand ??
          null,
      })
    )

  const velocity =
    data.baseline
      .velocity_cases_per_week

  const floorCases =
    velocity * 3

  const maxCases = Math.max(
    ...series.flatMap(
      (point) => [
        point.inventory_cases,
        point.skuba_inventory_cases ??
          0,
      ]
    ),
    floorCases,
    1
  )

  const yMax =
    Math.ceil(
      (maxCases * 1.15) / 10
    ) *
      10 || 10

  const primaryNewOrder =
    getPrimaryNewOrder(
      data.breaches
    )

  const primaryExpedite =
    getPrimaryExpedite(
      data.breaches
    )

  const confirmedEvents =
    useMemo(() => {
      return [
        ...data.baseline!
          .confirmed_po_events,
      ]
        .filter(
          (event) =>
            !event.is_stale &&
            Boolean(
              event.receipt_date ??
                event.expected_delivery_date
            )
        )
        .sort(
          (a, b) =>
            dateValue(
              a.receipt_date ??
                a.expected_delivery_date
            ) -
            dateValue(
              b.receipt_date ??
                b.expected_delivery_date
            )
        )
        .map(
          (
            event,
            index
          ): SupplyEvent => {
            const eventDate =
              event.receipt_date ??
              event.expected_delivery_date

            const trajectoryPoint =
              getInventoryAtDate(
                baselineTrajectory,
                eventDate
              )

            return {
              id: `confirmed-${index}-${eventDate}`,
              kind: "confirmed",
              cases: event.cases,
              date: eventDate,
              label:
                event.po_status ===
                "overdue"
                  ? "Confirmed PO · overdue"
                  : "Confirmed PO",
              status:
                event.po_status ===
                "overdue"
                  ? "Overdue"
                  : "Confirmed",
              secondary:
                trajectoryPoint
                  ? `${formatCases(
                      trajectoryPoint.inventory_cases
                    )} cases on hand upon delivery · ${formatOneDecimal(
                      trajectoryPoint.weeks_on_hand
                    )} WOH`
                  : null,
              inventoryOnDelivery:
                trajectoryPoint
                  ?.inventory_cases ??
                null,
              weeksOnHandOnDelivery:
                trajectoryPoint
                  ?.weeks_on_hand ??
                null,
            }
          }
        )
    }, [
      data.baseline,
      baselineTrajectory,
    ])

  /*
   * With the current API, projected
   * distributor orders are exposed through
   * breach evaluations rather than a
   * top-level projected-orders array.
   *
   * So this intentionally renders only the
   * projected orders that the API currently
   * exposes to this component.
   */
  const projectedEvents =
    useMemo(() => {
      const events: SupplyEvent[] =
        []

      const seen = new Set<
        string
      >()

      data.breaches.forEach(
        (breach, index) => {
          const projected =
            breach.projected_order

          const order =
            projected
              ?.resolving_order

          if (
            !projected?.exists ||
            !order ||
            order.cases == null ||
            !order.expected_delivery_date
          ) {
            return
          }

          const key = `${order.cases}-${order.expected_delivery_date}`

          if (seen.has(key)) {
            return
          }

          seen.add(key)

          events.push({
            id: `projected-${index}-${key}`,
            kind: "projected",
            cases: order.cases,
            date:
              order.expected_delivery_date,
            label:
              "Projected order",
            status:
              projected.resolves_breach
                ? "Resolves gap"
                : "Projected",
            secondary:
              projected.reason ??
              "Distributor-projected supply. Not committed.",
          })
        }
      )

      return events.sort(
        (a, b) =>
          dateValue(a.date) -
          dateValue(b.date)
      )
    }, [data.breaches])

  const skubaEvent =
    useMemo((): SupplyEvent | null => {
      if (
        !primaryNewOrder ||
        primaryNewOrder
          .recommended_cases <= 0
      ) {
        return null
      }

      const deliveryDate =
        primaryNewOrder
          .expected_delivery_date ??
        null

      const point =
        getInventoryAtDate(
          skubaTrajectory,
          deliveryDate
        )

      return {
        id: "skuba-order",
        kind: "skuba",
        cases:
          primaryNewOrder
            .recommended_cases,
        date: deliveryDate,
        label:
          "Recommended order",
        status: "Recommended",
        secondary: point
          ? `${formatCases(
              point.inventory_cases
            )} cases on hand upon delivery · ${formatOneDecimal(
              point.weeks_on_hand
            )} WOH`
          : primaryNewOrder
              .reason ??
            null,
        inventoryOnDelivery:
          point?.inventory_cases ??
          null,
        weeksOnHandOnDelivery:
          point?.weeks_on_hand ??
          null,
      }
    }, [
      primaryNewOrder,
      skubaTrajectory,
    ])

  const timelineEvents =
    useMemo(() => {
      return [
        ...confirmedEvents,
        ...projectedEvents,
        ...(skubaEvent
          ? [skubaEvent]
          : []),
      ]
    }, [
      confirmedEvents,
      projectedEvents,
      skubaEvent,
    ])

  const asOf =
    data.as_of_date ??
    data.baseline.as_of_date

  const orderIsLate =
    primaryNewOrder
      ?.order_by_date &&
    dateValue(
      primaryNewOrder.order_by_date
    ) < dateValue(asOf)

  const recommendationTitle =
    primaryNewOrder
      ? `${formatCases(
          primaryNewOrder.recommended_cases
        )} cases`
      : primaryExpedite
        ? "Follow up"
        : data.inventory_status ===
            "monitor"
          ? "Monitor"
          : "No action"

  const recommendationSubtitle =
    primaryNewOrder
      ? orderIsLate
        ? "Order ASAP"
        : primaryNewOrder
              .order_by_date
          ? `Order by ${formatDate(
              primaryNewOrder.order_by_date
            )}`
          : "New order recommended"
      : primaryExpedite
        ? "Expedite confirmed PO if possible"
        : data.inventory_status ===
            "monitor"
          ? "No additional order right now"
          : "Coverage remains healthy"

  return (
    <div className="w-full">
      {/* ------------------------------------------------
          TOP STORY
         ------------------------------------------------ */}

      <div className="grid gap-6 lg:grid-cols-[0.78fr_1.22fr] lg:items-center">
        <div>
          <div
            className="text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{
              color:
                theme.accent_color,
            }}
          >
            {primaryNewOrder ||
            primaryExpedite
              ? "SKUba recommendation"
              : "Inventory status"}
          </div>

          <div
            className="mt-2 text-[42px] font-semibold leading-none tracking-[-0.04em]"
            style={{
              color:
                primaryNewOrder ||
                primaryExpedite
                  ? accentColor
                  : theme.charcoal,
            }}
          >
            {recommendationTitle}
          </div>

          <div className="mt-2 text-sm text-[#8A8378]">
            {primaryNewOrder
              ? "recommended to order"
              : primaryExpedite
                ? "on confirmed supply"
                : ""}
          </div>

          <div
            className="mt-5 border-l-[3px] pl-3"
            style={{
              borderColor:
                primaryNewOrder ||
                primaryExpedite
                  ? accentColor
                  : "#55735E",
            }}
          >
            <div className="text-base font-semibold text-[#343332]">
              {
                recommendationSubtitle
              }
            </div>

            {primaryNewOrder &&
              data.planning_lead_time_days !=
                null && (
                <div className="mt-1 text-xs text-[#8A8378]">
                  {
                    data.planning_lead_time_days
                  }
                  -day planning lead time
                  {primaryNewOrder.expected_delivery_date
                    ? ` · modeled receipt ${formatDate(
                        primaryNewOrder.expected_delivery_date
                      )}`
                    : ""}
                </div>
              )}

            {primaryExpedite && (
              <div className="mt-1 text-xs text-[#8A8378]">
                {primaryExpedite.needed_by_date
                  ? `Needed by ${formatDate(
                      primaryExpedite.needed_by_date
                    )}`
                  : "Confirmed supply needs earlier arrival"}
              </div>
            )}
          </div>
        </div>

        <InventoryVelocityVisual
          data={data}
          accentColor={accentColor}
          theme={theme}
        />
      </div>

      {/* ------------------------------------------------
          WHY
         ------------------------------------------------ */}

      {data.narrative && (
        <div
          className="mt-5 rounded-[16px] border px-4 py-3 text-sm leading-6"
          style={{
            background:
              data.inventory_status ===
              "action"
                ? "#FBF2EE"
                : "#F7F4EE",
            borderColor:
              data.inventory_status ===
              "action"
                ? "#F0D9D0"
                : "#EEE5D8",
            color: "#705C4F",
          }}
        >
          <span
            className="font-semibold"
            style={{
              color:
                theme.charcoal,
            }}
          >
            Why this matters —{" "}
          </span>

          {data.narrative}
        </div>
      )}

      {/* ------------------------------------------------
          OUTLOOK + SUPPLY RAIL
         ------------------------------------------------ */}

      <div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="min-w-0">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div
                className="text-[11px] font-semibold uppercase tracking-[0.14em]"
                style={{
                  color:
                    theme.accent_color,
                }}
              >
                Inventory outlook
              </div>

              <div className="mt-1 text-xs text-[#8A8378]">
                Confirmed supply vs.
                SKUba-recommended supply
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <div
                  className="h-[3px] w-5 rounded-full"
                  style={{
                    backgroundColor:
                      accentColor,
                  }}
                />

                <span className="text-[10px] font-medium text-[#716A61]">
                  Confirmed supply
                </span>
              </div>

              <div className="flex items-center gap-2">
                <div
                  className="w-5 border-t-[3px] border-dashed"
                  style={{
                    borderColor:
                      theme.charcoal,
                  }}
                />

                <span className="text-[10px] font-medium text-[#716A61]">
                  With SKUba
                </span>
              </div>

              <div className="flex items-center gap-2">
                <div className="w-5 border-t border-dashed border-[#C9A96E]" />

                <span className="text-[10px] font-medium text-[#716A61]">
                  3 WOH floor
                </span>
              </div>
            </div>
          </div>

          <SupplyTimeline
            data={data}
            events={timelineEvents}
            accentColor={
              accentColor
            }
            theme={theme}
          />

          <div className="h-[320px] w-full">
            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <LineChart
                data={series}
                margin={{
                  top: 24,
                  right: 18,
                  left: -4,
                  bottom: 0,
                }}
              >
                <CartesianGrid
                  vertical={false}
                  stroke={
                    theme.line
                  }
                  strokeDasharray="3 3"
                />

                <XAxis
                  dataKey="date"
                  tickFormatter={
                    formatDate
                  }
                  tickLine={false}
                  axisLine={false}
                  tickMargin={10}
                  minTickGap={28}
                  tick={{
                    fontSize: 11,
                    fill: "#8A8378",
                  }}
                />

                <YAxis
                  domain={[0, yMax]}
                  tickFormatter={
                    formatCases
                  }
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  width={48}
                  tick={{
                    fontSize: 11,
                    fill: "#8A8378",
                  }}
                  label={{
                    value: "Cases",
                    angle: -90,
                    position:
                      "insideLeft",
                    fill: "#9A9389",
                    fontSize: 10,
                    offset: 8,
                  }}
                />

                <Tooltip
                  cursor={{
                    stroke:
                      "#D8D1C6",
                    strokeDasharray:
                      "3 3",
                  }}
                  content={
                    <OutlookTooltip
                      floorCases={
                        floorCases
                      }
                      confirmedEvents={
                        data.baseline
                          .confirmed_po_events
                      }
                      skubaOrder={
                        primaryNewOrder
                      }
                      baselineTrajectory={
                        baselineTrajectory
                      }
                      skubaTrajectory={
                        skubaTrajectory
                      }
                    />
                  }
                />

                <ReferenceLine
                  y={floorCases}
                  stroke="#C9A96E"
                  strokeWidth={1.5}
                  strokeDasharray="5 5"
                  label={{
                    value:
                      "3 WOH floor",
                    position:
                      "insideTopRight",
                    fill:
                      "#9A7A42",
                    fontSize: 10,
                    fontWeight: 600,
                  }}
                />

                <Line
                  type="linear"
                  dataKey="inventory_cases"
                  name="Confirmed supply"
                  stroke={accentColor}
                  strokeWidth={3}
                  dot={false}
                  activeDot={{
                    r: 5,
                    fill:
                      theme.surface,
                    stroke:
                      accentColor,
                    strokeWidth: 2,
                  }}
                />

                <Line
                  type="linear"
                  dataKey="skuba_inventory_cases"
                  name="With SKUba"
                  stroke={
                    theme.charcoal
                  }
                  strokeWidth={3}
                  strokeDasharray="7 5"
                  dot={false}
                  connectNulls
                  activeDot={{
                    r: 5,
                    fill:
                      theme.surface,
                    stroke:
                      theme.charcoal,
                    strokeWidth: 2,
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <SupplyRail
          confirmedEvents={
            confirmedEvents
          }
          projectedEvents={
            projectedEvents
          }
          skubaEvent={
            skubaEvent
          }
          accentColor={
            accentColor
          }
          theme={theme}
        />
      </div>
    </div>
  )
}