"use client"

import { useState } from "react"
import { Package } from "lucide-react"

import {
  InventoryAssessment,
  InventoryOutlook,
} from "@/components/inventory/InventoryOutlook"

const theme = {
  accent: "#C8795A",
  charcoal: "#343332",
  brown: "#705C4F",
  line: "#E5DDD0",
  surface: "#FFFDF9",
  softSurface: "#FCFAF6",
  softLine: "#EEE5D8",
  coralDark: "#D9532F",
}

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"

const SKU_IMAGES: Record<
  string,
  { src: string; scale: number; x?: number }
> = {
  "VANILLA BEAN": {
    src: "/skus/smearcase-vanilla-bean.png",
    scale: 1.18,
  },
  "MOCHA JOE": {
    src: "/skus/smearcase-mocha-joe.png",
    scale: 1.14,
    x: -5,
  },
  STRAWBERRY: {
    src: "/skus/smearcase-strawberry.png",
    scale: 1.0,
  },
  "PEANUT BUTTER": {
    src: "/skus/smearcase-peanut-butter.png",
    scale: 0.92,
  },
}

type OverviewIntervention = {
  reaches_oos?: boolean | null
  first_oos_date?: string | null
  lowest_woh?: number | null
  lowest_woh_date?: string | null
  first_tolerance_breach_date?: string | null
  intervention_required?: boolean | null
  intervention_type?: string | null
  recommended_cases?: number | null
  order_by_date?: string | null
  needed_by_date?: string | null
  expected_delivery_date?: string | null
  po_cases?: number | null
  current_po_receipt_date?: string | null
}

export type OverviewInventorySku = {
  distributor: string
  dc: string
  sku: string
  product_name?: string | null

  inventory_status:
    | "action"
    | "monitor"
    | "healthy"
    | "projection_unavailable"

  inventory_urgency?: "critical" | "high" | "normal" | null

  po_status?: string | null
  has_active_po?: boolean | null
  has_overdue_po?: boolean | null
  has_stale_po?: boolean | null
  has_projected_order?: boolean | null
  has_resolving_projected_order?: boolean | null

  days_until_oos?: number | null
  days_of_cushion?: number | null
  planning_lead_time_days?: number | null

  interventions: OverviewIntervention[]
}

type SkuInventoryCardProps = {
  sku: OverviewInventorySku
  skuColor: string
  orgId: string
}

function formatNumber(
  value: number | null | undefined,
  digits = 0
) {
  if (value == null || Number.isNaN(value)) {
    return "—"
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function formatDate(
  value: string | null | undefined
) {
  if (!value) return "—"

  const date = new Date(`${value}T00:00:00`)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  })
}

function dateValue(
  value: string | null | undefined
) {
  if (!value) {
    return Number.POSITIVE_INFINITY
  }

  return new Date(`${value}T00:00:00`).getTime()
}

function getStatusLabel(
  status: OverviewInventorySku["inventory_status"]
) {
  if (status === "action") {
    return "Needs action"
  }

  if (status === "monitor") {
    return "Monitoring"
  }

  if (status === "projection_unavailable") {
    return "Projection unavailable"
  }

  return "Healthy"
}

function getPrimaryOrder(
  sku: OverviewInventorySku
) {
  return sku.interventions.find(
    (intervention) =>
      intervention.intervention_type === "new_order" &&
      intervention.intervention_required !== false
  )
}

function getExpediteIntervention(
  sku: OverviewInventorySku
) {
  return sku.interventions.find(
    (intervention) =>
      intervention.intervention_type === "expedite_po"
  )
}

function getInventoryRisk(
  sku: OverviewInventorySku
) {
  if (
    sku.days_until_oos != null &&
    sku.days_until_oos <= 0
  ) {
    return "Already out of stock"
  }

  const firstOosDate = sku.interventions
    .map((intervention) => intervention.first_oos_date)
    .filter(
      (value): value is string => Boolean(value)
    )
    .sort(
      (a, b) => dateValue(a) - dateValue(b)
    )[0]

  if (firstOosDate) {
    return `OOS ${formatDate(firstOosDate)}`
  }

  const lowestWohValues = sku.interventions
    .map((intervention) => intervention.lowest_woh)
    .filter(
      (value): value is number =>
        value != null && Number.isFinite(value)
    )

  if (
    lowestWohValues.length > 0 &&
    Math.min(...lowestWohValues) < 3
  ) {
    return "Below inventory floor"
  }

  if (sku.inventory_status === "projection_unavailable") {
    return "Projection unavailable"
  }

  if (sku.inventory_status === "monitor") {
    return "Inventory needs monitoring"
  }

  return "Inventory healthy"
}

function getPoDisplay(
  sku: OverviewInventorySku
) {
  const expedite = getExpediteIntervention(sku)

  if (sku.has_stale_po) {
    return {
      label: "Open PO",
      title: "Stale PO",
      detail: "Needs review",
    }
  }

  if (sku.has_overdue_po) {
    return {
      label: "Open PO",
      title:
        expedite?.po_cases != null
          ? `${formatNumber(expedite.po_cases)} cases`
          : "PO overdue",
      detail: "Overdue",
    }
  }

  if (sku.has_active_po) {
    const poCases =
      expedite?.po_cases ??
      sku.interventions.find(
        (intervention) =>
          intervention.po_cases != null
      )?.po_cases

    const receiptDate =
      expedite?.current_po_receipt_date ??
      sku.interventions.find(
        (intervention) =>
          intervention.current_po_receipt_date
      )?.current_po_receipt_date

    return {
      label: "Open PO",
      title:
        poCases != null
          ? `+${formatNumber(poCases)} cases`
          : "Open PO",
      detail: receiptDate
        ? `Expected ${formatDate(receiptDate)}`
        : null,
    }
  }

  return {
    label: "Open POs",
    title: "No open POs",
    detail: null,
  }
}

export default function SkuInventoryCard({
  sku,
  skuColor,
  orgId,
}: SkuInventoryCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [assessment, setAssessment] =
    useState<InventoryAssessment | null>(null)
  const [loadingAssessment, setLoadingAssessment] =
    useState(false)
  const [assessmentError, setAssessmentError] =
    useState<string | null>(null)

  const productImage = SKU_IMAGES[sku.sku]

  const primaryOrder = getPrimaryOrder(sku)
  const expediteIntervention =
    getExpediteIntervention(sku)

  const recommendedCases =
    sku.interventions.reduce(
      (sum, intervention) => {
        if (
          intervention.intervention_required &&
          intervention.intervention_type !==
            "future_replenishment" &&
          intervention.intervention_type !==
            "monitor_projected_order"
        ) {
          return (
            sum +
            (intervention.recommended_cases ?? 0)
          )
        }

        return sum
      },
      0
    )

  const hasExpedite = Boolean(expediteIntervention)

  const neededByDate =
    expediteIntervention?.needed_by_date ??
    primaryOrder?.needed_by_date ??
    null

  const orderIsPastDue =
    Boolean(
      primaryOrder?.order_by_date &&
        dateValue(primaryOrder.order_by_date) <
          new Date().setHours(0, 0, 0, 0)
    )

  const recommendationTitle =
    recommendedCases > 0
      ? `Order ${formatNumber(recommendedCases)} cases`
      : hasExpedite
        ? "Follow up on PO"
        : "No new order"

  const recommendationTiming =
    recommendedCases > 0
      ? primaryOrder?.order_by_date
        ? orderIsPastDue
          ? "ASAP"
          : `By ${formatDate(
              primaryOrder.order_by_date
            )}`
        : null
      : hasExpedite
        ? neededByDate
          ? `Needed by ${formatDate(
              neededByDate
            )} · No new order`
          : "No new order"
        : null

  const inventoryRisk = getInventoryRisk(sku)
  const poDisplay = getPoDisplay(sku)

  const handleToggle = async () => {
    if (expanded) {
      setExpanded(false)
      return
    }

    setExpanded(true)

    if (assessment || loadingAssessment) {
      return
    }

    setLoadingAssessment(true)
    setAssessmentError(null)

    try {
      const params = new URLSearchParams({
        org_id: orgId,
        distributor: sku.distributor,
        dc: sku.dc,
        sku: sku.sku,
      })

    const response = await fetch(
    `${API_BASE_URL}/inventory/projection?${params.toString()}`,
    { cache: "no-store" }
    )

      if (!response.ok) {
        throw new Error(
          `Projection request failed with ${response.status}`
        )
      }

      const payload: InventoryAssessment =
        await response.json()

      setAssessment(payload)
    } catch (error) {
      console.error(
        "Failed to load inventory projection:",
        error
      )

      setAssessmentError(
        "Unable to load the inventory plan."
      )
    } finally {
      setLoadingAssessment(false)
    }
  }

  return (
    <div
      className="overflow-hidden rounded-[22px] border transition"
      style={{
        background: theme.softSurface,
        borderColor: expanded
          ? "#D9CFC1"
          : theme.softLine,
      }}
    >
      <button
        type="button"
        onClick={handleToggle}
        className="w-full text-left"
        aria-expanded={expanded}
      >
        <div className="grid overflow-hidden lg:grid-cols-[135px_minmax(180px,0.9fr)_175px_220px_1px_260px] lg:items-stretch">
          {/* PRODUCT */}
          <div
            className="flex min-h-[170px] items-center justify-center overflow-hidden p-3"
            style={{
              backgroundColor: `${skuColor}0D`,
            }}
          >
            {productImage ? (
              <img
                src={productImage.src}
                alt={sku.product_name ?? sku.sku}
                className="h-[145px] w-[130px] object-contain"
                style={{
                  transform:
                    `translateX(${productImage.x ?? 0}px) scale(${productImage.scale})`,
                }}
              />
            ) : (
              <Package
                className="h-8 w-8"
                style={{ color: skuColor }}
              />
            )}
          </div>

          {/* SKU */}
          <div className="flex min-w-0 flex-col justify-center px-6 py-5">
            <div
              className="text-[16px] font-bold tracking-[-0.015em]"
              style={{ color: theme.charcoal }}
            >
              {sku.product_name ?? sku.sku}
            </div>

            <div className="mt-3">
              <span
                className="inline-flex rounded-full border px-3 py-1 text-[9px] font-bold uppercase tracking-[0.13em]"
                style={{
                  color: theme.coralDark,
                  borderColor: "#F2B9AA",
                  background: "#FFF7F3",
                }}
              >
                {getStatusLabel(sku.inventory_status)}
              </span>
            </div>

            {sku.days_of_cushion != null && (
              <div
                className="mt-3 text-[12px] font-medium"
                style={{ color: theme.brown }}
              >
                {formatNumber(
                  sku.days_of_cushion,
                  1
                )}{" "}
                days of cushion
              </div>
            )}
          </div>

          {/* PO */}
          <div className="flex min-w-0 flex-col justify-center border-l px-5 py-5"
            style={{ borderColor: theme.softLine }}
          >
            <div
              className="text-[9px] font-bold uppercase tracking-[0.18em]"
              style={{ color: "#8C7D70" }}
            >
              {poDisplay.label}
            </div>

            <div
              className="mt-2 text-[16px] font-bold leading-snug"
              style={{ color: theme.charcoal }}
            >
              {poDisplay.title}
            </div>

            {poDisplay.detail && (
              <div
                className="mt-1 text-[12px] font-semibold"
                style={{
                  color:
                    sku.has_overdue_po ||
                    sku.has_stale_po
                      ? theme.coralDark
                      : theme.brown,
                }}
              >
                {poDisplay.detail}
              </div>
            )}
          </div>

          {/* INVENTORY RISK */}
          <div
            className="flex min-w-0 flex-col justify-center border-l px-5 py-5"
            style={{ borderColor: theme.softLine }}
          >
            <div
              className="text-[9px] font-bold uppercase tracking-[0.18em]"
              style={{ color: "#8C7D70" }}
            >
              Inventory risk
            </div>

            <div
              className="mt-2 text-[16px] font-bold leading-snug"
              style={{ color: theme.charcoal }}
            >
              {inventoryRisk}
            </div>

            <div
              className="mt-2 text-[12px] font-medium"
              style={{ color: theme.brown }}
            >
              {sku.planning_lead_time_days != null
                ? `${formatNumber(
                    sku.planning_lead_time_days
                  )}-day lead time`
                : "Lead time unavailable"}
            </div>
          </div>

          {/* DIVIDER */}
          <div
            className="hidden w-px lg:block"
            style={{
              background: theme.softLine,
            }}
          />

          {/* RECOMMENDATION */}
          <div className="flex min-w-0 flex-col justify-center px-6 py-5">
            <div
              className="text-[9px] font-bold uppercase tracking-[0.18em]"
              style={{ color: "#7E7064" }}
            >
              SKUba recommends
            </div>

            <div
              className="mt-2 text-[25px] font-bold leading-[1.05] tracking-[-0.04em]"
              style={{ color: skuColor }}
            >
              {recommendationTitle}
            </div>

            {recommendationTiming && (
              <div
                className="mt-2 text-[11px] font-semibold uppercase tracking-[0.08em]"
                style={{ color: theme.brown }}
              >
                {recommendationTiming}
              </div>
            )}

            <div
              className="mt-4 flex items-center gap-2 text-[12px] font-bold"
              style={{ color: theme.charcoal }}
            >
              {expanded
                ? "Hide inventory plan"
                : "View inventory plan"}

              <span
                className="text-[16px] font-normal leading-none"
                aria-hidden="true"
              >
                {expanded ? "↑" : "→"}
              </span>
            </div>
          </div>
        </div>
      </button>

      {expanded && (
        <div
          className="border-t px-5 pb-6 pt-5 md:px-6"
          style={{
            borderColor: theme.softLine,
            background: theme.surface,
          }}
        >
          {loadingAssessment && (
            <div
              className="flex min-h-[160px] items-center justify-center text-[14px] font-medium"
              style={{ color: theme.brown }}
            >
              Loading inventory plan...
            </div>
          )}

          {!loadingAssessment &&
            assessmentError && (
              <div
                className="flex min-h-[120px] items-center justify-center text-[14px] font-medium"
                style={{ color: theme.coralDark }}
              >
                {assessmentError}
              </div>
            )}

          {!loadingAssessment &&
            !assessmentError &&
            assessment && (
              <InventoryOutlook
                data={assessment}
                accentColor={skuColor}
                theme={{
                  surface: theme.surface,
                  line: theme.line,
                  accent_color: skuColor,
                  charcoal: theme.charcoal,
                }}
              />
            )}
        </div>
      )}
    </div>
  )
}