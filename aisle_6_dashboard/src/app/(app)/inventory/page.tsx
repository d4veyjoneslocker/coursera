"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  CircleAlert,
  PackageCheck,
  RefreshCw,
  Truck,
} from "lucide-react"

type InventorySummary = {
  dc_count: number
  dcs_needing_action: number
  dcs_monitoring_inbound: number
  dcs_needing_review: number
  known_recommended_cases: number
}

type DistributionCenter = {
  distributor: string
  dc: string

  status:
    | "critical"
    | "needs_attention"
    | "review"
    | "healthy"
    | "unknown"

  quantity_needed_cases: number | null
  recommendation_complete: boolean

  weeks_on_hand: number | null
  weeks_with_inbound: number | null
  planning_lead_time_days: number | null

  monitor_inbound: boolean
  order_needed: boolean

  sku_count: number
  skus_needing_order: number

  quantity_on_hand_cases: number | null
  quantity_on_po_cases: number | null

  units_per_week: number | null
  cases_per_week: number | null
}

type InventoryOverviewResponse = {
  summary: InventorySummary
  distribution_centers: DistributionCenter[]
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL

function formatNumber(
  value: number | null | undefined,
  digits = 0
) {
  if (value === null || value === undefined) {
    return "—"
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function formatWeeks(
  value: number | null | undefined
) {
  if (value === null || value === undefined) {
    return "—"
  }

  return `${value.toFixed(1)} wks`
}

function formatLeadTime(
  value: number | null | undefined
) {
  if (value === null || value === undefined) {
    return "Not set"
  }

  const rounded = Math.round(value * 10) / 10

  return `${rounded} day${rounded === 1 ? "" : "s"}`
}

function getStatusLabel(
  status: DistributionCenter["status"]
) {
  switch (status) {
    case "critical":
      return "Critical"

    case "needs_attention":
      return "Needs attention"

    case "review":
      return "Review"

    case "healthy":
      return "Healthy"

    default:
      return "Unknown"
  }
}

function getStatusClasses(
  status: DistributionCenter["status"]
) {
  switch (status) {
    case "critical":
      return "border-[#F0C8BE] bg-[#FFF1EC] text-[#B94A30]"

    case "needs_attention":
      return "border-[#E8D5B5] bg-[#FFF8E8] text-[#8A651F]"

    case "review":
      return "border-[#DED8E8] bg-[#F5F2FA] text-[#6D6681]"

    case "healthy":
      return "border-[#CFE2D6] bg-[#F1F8F3] text-[#55735E]"

    default:
      return "border-[#E5DDD0] bg-[#F6F2EA] text-[#705C4F]"
  }
}

function SummaryCard({
  icon,
  value,
  label,
  detail,
}: {
  icon: React.ReactNode
  value: string
  label: string
  detail: string
}) {
  return (
    <div className="rounded-[24px] border border-[#E5DDD0] bg-[#FFFDF9] p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[28px] font-semibold tracking-[-0.03em] text-[#343332]">
            {value}
          </div>

          <div className="mt-1 text-sm font-medium text-[#343332]">
            {label}
          </div>

          <div className="mt-1 text-xs leading-5 text-[#8A8179]">
            {detail}
          </div>
        </div>

        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#F6F2EA] text-[#705C4F]">
          {icon}
        </div>
      </div>
    </div>
  )
}

function DcCard({
  dc,
  onClick,
}: {
  dc: DistributionCenter
  onClick: () => void
}) {
  const hasInbound =
    dc.monitor_inbound &&
    (dc.quantity_on_po_cases ?? 0) > 0

  const coverageImproves =
    dc.weeks_on_hand !== null &&
    dc.weeks_with_inbound !== null &&
    dc.weeks_with_inbound > dc.weeks_on_hand

  return (
    <button
      type="button"
      onClick={onClick}
      className="group w-full cursor-pointer rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] p-5 text-left shadow-sm transition hover:-translate-y-[1px] hover:border-[#D8CCBC] hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-base font-semibold text-[#343332]">
              {dc.distributor} · {dc.dc}
            </div>

            <div
              className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${getStatusClasses(
                dc.status
              )}`}
            >
              {getStatusLabel(dc.status)}
            </div>

            {dc.monitor_inbound && (
              <div className="rounded-full border border-[#D8D2E5] bg-[#F6F3FA] px-2.5 py-1 text-[11px] font-medium text-[#6E6683]">
                Inbound
              </div>
            )}
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-4">
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#A09890]">
                On hand
              </div>

              <div className="mt-1 text-sm font-semibold text-[#343332]">
                {formatNumber(dc.quantity_on_hand_cases)} cases
              </div>

              <div className="mt-1 text-xs text-[#8A8179]">
                current quantity
              </div>
            </div>

            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#A09890]">
                Coverage
              </div>

              <div className="mt-1 text-sm font-semibold text-[#343332]">
                {formatWeeks(dc.weeks_on_hand)}

                {coverageImproves && (
                  <span className="font-normal text-[#8A8179]">
                    {" "}
                    → {formatWeeks(dc.weeks_with_inbound)}
                  </span>
                )}
              </div>

              <div className="mt-1 text-xs text-[#8A8179]">
                {coverageImproves
                  ? "with inbound inventory"
                  : "current weeks on hand"}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#A09890]">
                Recommendation
              </div>

              <div className="mt-1 text-sm font-semibold text-[#343332]">
                {dc.recommendation_complete
                  ? `${formatNumber(
                      dc.quantity_needed_cases
                    )} cases`
                  : "Needs setup"}
              </div>

              <div className="mt-1 text-xs text-[#8A8179]">
                {dc.recommendation_complete
                  ? dc.order_needed
                    ? `${dc.skus_needing_order} SKU${
                        dc.skus_needing_order === 1
                          ? ""
                          : "s"
                      } need replenishment`
                    : "No replenishment required"
                  : dc.planning_lead_time_days === null
                    ? "Lead time required"
                    : "Recommendation unavailable"}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#A09890]">
                Lead time
              </div>

              <div className="mt-1 text-sm font-semibold text-[#343332]">
                {formatLeadTime(
                  dc.planning_lead_time_days
                )}
              </div>

              <div className="mt-1 text-xs text-[#8A8179]">
                {hasInbound
                  ? `${formatNumber(
                      dc.quantity_on_po_cases
                    )} cases currently inbound`
                  : `${formatNumber(
                      dc.cases_per_week,
                      1
                    )} cases / week`}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[#E5DDD0] bg-[#FCFAF6] text-[#705C4F] transition group-hover:border-[#C8795A] group-hover:text-[#C8795A]">
          <ArrowRight className="h-4 w-4" />
        </div>
      </div>
    </button>
  )
}

function HealthyRow({
  dc,
  onClick,
}: {
  dc: DistributionCenter
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full cursor-pointer items-center justify-between gap-4 border-b border-[#EEE5D8] px-1 py-4 text-left last:border-b-0"
    >
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#F1F6F2] text-[#55735E]">
          <PackageCheck className="h-4 w-4" />
        </div>

        <div>
          <div className="font-medium text-[#343332]">
            {dc.distributor} · {dc.dc}
          </div>

          <div className="mt-0.5 text-xs text-[#8A8179]">
            {formatNumber(dc.quantity_on_hand_cases)} cases on hand ·{" "}
            {dc.sku_count} SKU
            {dc.sku_count === 1 ? "" : "s"}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden text-right sm:block">
          <div className="text-sm font-semibold text-[#343332]">
            {formatWeeks(dc.weeks_on_hand)}
          </div>

          <div className="text-xs text-[#8A8179]">
            coverage
          </div>
        </div>

        <ArrowRight className="h-4 w-4 text-[#A59C93] transition group-hover:text-[#C8795A]" />
      </div>
    </button>
  )
}

export default function InventoryPage() {
  const router = useRouter()

  const [data, setData] =
    useState<InventoryOverviewResponse | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] =
    useState<string | null>(null)

  const loadInventory = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()

      /*
       * Keep this consistent with however you currently
       * pass the valid org UUID to this endpoint.
       *
       * If you already changed this successfully,
       * leave your working org_id line here.
       */
      const orgId =
        "PUT_YOUR_EXISTING_WORKING_ORG_UUID_HERE"

      params.set("org_id", orgId)

      const response = await fetch(
        `${API_BASE_URL}/inventory/overview?${params.toString()}`
      )

      if (!response.ok) {
        throw new Error(
          `Inventory overview failed: ${response.status}`
        )
      }

      const json: InventoryOverviewResponse =
        await response.json()

      setData(json)
    } catch (err) {
      console.error(
        "Failed to load inventory overview:",
        err
      )

      setError(
        "Unable to load inventory planning."
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInventory()
  }, [])

  const {
    actionDcs,
    reviewDcs,
    healthyDcs,
  } = useMemo(() => {
    const action: DistributionCenter[] = []
    const review: DistributionCenter[] = []
    const healthy: DistributionCenter[] = []

    for (const dc of
      data?.distribution_centers ?? []) {
      if (
        !dc.recommendation_complete ||
        dc.status === "review"
      ) {
        review.push(dc)
        continue
      }

      if (
        dc.order_needed ||
        dc.status === "critical" ||
        dc.status === "needs_attention"
      ) {
        action.push(dc)
        continue
      }

      healthy.push(dc)
    }

    return {
      actionDcs: action,
      reviewDcs: review,
      healthyDcs: healthy,
    }
  }, [data])

  const openDc = (dc: DistributionCenter) => {
    router.push(
      `/inventory/${encodeURIComponent(
        dc.distributor
      )}/${encodeURIComponent(dc.dc)}`
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F6F2EA] px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <div className="flex min-h-[420px] items-center justify-center">
            <div className="flex items-center gap-3 rounded-full border border-[#E5DDD0] bg-[#FFFDF9] px-5 py-3 text-sm text-[#705C4F] shadow-sm">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Loading inventory planning
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-[#F6F2EA] px-6 py-10">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-[26px] border border-[#F0C8BE] bg-[#FFF7F4] p-6">
            <div className="flex items-start gap-3">
              <CircleAlert className="mt-0.5 h-5 w-5 text-[#C8795A]" />

              <div>
                <div className="font-semibold text-[#343332]">
                  Inventory planning could not load
                </div>

                <div className="mt-1 text-sm text-[#8A8179]">
                  {error ??
                    "No inventory data was returned."}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-[#F6F2EA] p-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9A93B0]">
            Inventory
          </div>

          <h1 className="mt-2 text-[34px] font-semibold tracking-[-0.04em] text-[#343332]">
            Inventory Planning
          </h1>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#7C746D]">
            See where inventory is tight, what is
            already inbound, and where replenishment
            is needed next.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            icon={
              <AlertTriangle className="h-5 w-5" />
            }
            value={formatNumber(
              data.summary.dcs_needing_action
            )}
            label="DCs need replenishment"
            detail="Locations with a calculated order recommendation"
          />

          <SummaryCard
            icon={<Boxes className="h-5 w-5" />}
            value={formatNumber(
              data.summary.known_recommended_cases
            )}
            label="Cases recommended"
            detail="Known replenishment across calculable DCs"
          />

          <SummaryCard
            icon={<Truck className="h-5 w-5" />}
            value={formatNumber(
              data.summary.dcs_monitoring_inbound
            )}
            label="Inbound to monitor"
            detail="DCs with open purchase orders"
          />

          <SummaryCard
            icon={
              <CircleAlert className="h-5 w-5" />
            }
            value={formatNumber(
              data.summary.dcs_needing_review
            )}
            label="DCs need review"
            detail="Locations without active demand signals"
          />
        </div>

        <div className="grid gap-8 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,0.8fr)]">
          <section>
            <div className="mb-4 flex items-end justify-between gap-4">
              <div>
                <div className="text-lg font-semibold tracking-[-0.02em] text-[#343332]">
                  Needs action
                </div>

                <div className="mt-1 text-sm text-[#8A8179]">
                  Prioritized locations where inventory
                  needs operator attention.
                </div>
              </div>

              <div className="text-xs font-medium text-[#A09890]">
                {actionDcs.length} location
                {actionDcs.length === 1 ? "" : "s"}
              </div>
            </div>

            <div className="space-y-3">
              {actionDcs.length > 0 ? (
                actionDcs.map((dc) => (
                  <DcCard
                    key={`${dc.distributor}-${dc.dc}`}
                    dc={dc}
                    onClick={() => openDc(dc)}
                  />
                ))
              ) : (
                <div className="rounded-[26px] border border-[#DDE7DF] bg-[#F7FBF8] p-6">
                  <div className="font-semibold text-[#55735E]">
                    No replenishment actions right now
                  </div>

                  <div className="mt-1 text-sm text-[#789080]">
                    Current calculable locations are
                    sufficiently covered.
                  </div>
                </div>
              )}
            </div>
          </section>

          <section>
            <div className="mb-4">
              <div className="text-lg font-semibold tracking-[-0.02em] text-[#343332]">
                Needs setup or review
              </div>

              <div className="mt-1 text-sm text-[#8A8179]">
                Locations where SKUba cannot yet make a
                complete recommendation.
              </div>
            </div>

            <div className="overflow-hidden rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] shadow-sm">
              {reviewDcs.length > 0 ? (
                reviewDcs.map((dc) => {
                  const missingLeadTime =
                    dc.planning_lead_time_days ===
                      null &&
                    !dc.recommendation_complete

                  return (
                    <button
                      type="button"
                      key={`${dc.distributor}-${dc.dc}`}
                      onClick={() => openDc(dc)}
                      className="group w-full cursor-pointer border-b border-[#EEE5D8] p-4 text-left last:border-b-0 hover:bg-[#FCFAF6]"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <div className="font-semibold text-[#343332]">
                              {dc.distributor} · {dc.dc}
                            </div>

                            <div
                              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${getStatusClasses(
                                dc.status
                              )}`}
                            >
                              {getStatusLabel(dc.status)}
                            </div>
                          </div>

                          <div className="mt-2 text-xs leading-5 text-[#8A8179]">
                            {missingLeadTime
                              ? "Lead time required to calculate replenishment."
                              : dc.weeks_on_hand ===
                                  null
                                ? "No active demand detected for this location."
                                : `${formatWeeks(
                                    dc.weeks_on_hand
                                  )} current coverage.`}
                          </div>

                          <div className="mt-2 text-xs font-medium text-[#705C4F]">
                            {formatNumber(
                              dc.quantity_on_hand_cases
                            )}{" "}
                            cases on hand
                          </div>

                          {dc.monitor_inbound && (
                            <div className="mt-2 flex items-center gap-1.5 text-xs font-medium text-[#6E6683]">
                              <Truck className="h-3.5 w-3.5" />

                              {formatNumber(
                                dc.quantity_on_po_cases
                              )}{" "}
                              cases inbound
                            </div>
                          )}
                        </div>

                        <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-[#A59C93] transition group-hover:text-[#C8795A]" />
                      </div>
                    </button>
                  )
                })
              ) : (
                <div className="p-5 text-sm text-[#8A8179]">
                  No locations currently need review.
                </div>
              )}
            </div>
          </section>
        </div>

        <section>
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <div className="text-lg font-semibold tracking-[-0.02em] text-[#343332]">
                Healthy locations
              </div>

              <div className="mt-1 text-sm text-[#8A8179]">
                Locations with no current replenishment
                action required.
              </div>
            </div>

            <div className="text-xs font-medium text-[#A09890]">
              {healthyDcs.length} location
              {healthyDcs.length === 1 ? "" : "s"}
            </div>
          </div>

          <div className="rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] px-5 shadow-sm">
            {healthyDcs.length > 0 ? (
              healthyDcs.map((dc) => (
                <HealthyRow
                  key={`${dc.distributor}-${dc.dc}`}
                  dc={dc}
                  onClick={() => openDc(dc)}
                />
              ))
            ) : (
              <div className="py-5 text-sm text-[#8A8179]">
                No healthy locations to show.
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}