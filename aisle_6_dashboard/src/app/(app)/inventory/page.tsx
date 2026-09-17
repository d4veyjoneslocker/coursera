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
  dcs_monitoring: number
  dcs_needing_review: number
  dcs_with_projection_unavailable: number
  known_recommended_cases: number
}

type DistributionCenter = {
  distributor: string
  dc: string
  sku_count: number
  skus_needing_action: number
  skus_monitoring: number
  skus_healthy: number
  skus_needing_review: number
  skus_projection_unavailable: number
  skus_to_expedite: number
  skus_needing_new_order: number
  skus_monitoring_projected_order: number
  quantity_needed_cases: number
  recommendation_complete: boolean
}

type InventoryOverviewResponse = {
  summary: InventorySummary
  distribution_centers: DistributionCenter[]
}

type DcStatus =
  | "needs_attention"
  | "monitoring"
  | "review"
  | "healthy"

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000"

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

function pluralize(
  count: number,
  singular: string,
  plural = `${singular}s`
) {
  return count === 1 ? singular : plural
}

function getDcStatus(
  dc: DistributionCenter
): DcStatus {
  if (
    !dc.recommendation_complete ||
    dc.skus_needing_review > 0 ||
    dc.skus_projection_unavailable > 0
  ) {
    return "review"
  }

  if (dc.skus_needing_action > 0) {
    return "needs_attention"
  }

  if (dc.skus_monitoring > 0) {
    return "monitoring"
  }

  return "healthy"
}

function getStatusLabel(status: DcStatus) {
  if (status === "needs_attention") {
    return "Needs attention"
  }

  if (status === "monitoring") {
    return "Monitoring"
  }

  if (status === "review") {
    return "Review"
  }

  return "Healthy"
}

function getStatusClasses(status: DcStatus) {
  if (status === "needs_attention") {
    return "border-[#E8D5B5] bg-[#FFF8E8] text-[#8A651F]"
  }

  if (status === "monitoring") {
    return "border-[#D8D2E5] bg-[#F6F3FA] text-[#6E6683]"
  }

  if (status === "review") {
    return "border-[#DED8E8] bg-[#F5F2FA] text-[#6D6681]"
  }

  return "border-[#CFE2D6] bg-[#F1F8F3] text-[#55735E]"
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
  const status = getDcStatus(dc)

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
                status
              )}`}
            >
              {getStatusLabel(status)}
            </div>

            {dc.skus_monitoring > 0 && (
              <div className="rounded-full border border-[#D8D2E5] bg-[#F6F3FA] px-2.5 py-1 text-[11px] font-medium text-[#6E6683]">
                {dc.skus_monitoring} monitoring
              </div>
            )}
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-4">
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#A09890]">
                Action
              </div>

              <div className="mt-1 text-sm font-semibold text-[#343332]">
                {dc.skus_needing_action}{" "}
                {pluralize(
                  dc.skus_needing_action,
                  "SKU"
                )}
              </div>

              <div className="mt-1 text-xs text-[#8A8179]">
                of {dc.sku_count} active{" "}
                {pluralize(dc.sku_count, "SKU")}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#A09890]">
                Actions
              </div>

              <div className="mt-1 text-sm font-semibold text-[#343332]">
                {dc.skus_to_expedite > 0
                  ? `${dc.skus_to_expedite} expedite`
                  : dc.skus_needing_new_order > 0
                    ? `${dc.skus_needing_new_order} new order`
                    : "None"}
              </div>

              <div className="mt-1 text-xs text-[#8A8179]">
                {dc.skus_to_expedite > 0 &&
                dc.skus_needing_new_order > 0
                  ? `${dc.skus_needing_new_order} also need new orders`
                  : dc.skus_monitoring_projected_order >
                      0
                    ? `${dc.skus_monitoring_projected_order} projected order monitored`
                    : "Current engine actions"}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#A09890]">
                Recommendation
              </div>

              <div className="mt-1 text-sm font-semibold text-[#343332]">
                {formatNumber(
                  dc.quantity_needed_cases
                )}{" "}
                cases
              </div>

              <div className="mt-1 text-xs text-[#8A8179]">
                {dc.quantity_needed_cases > 0
                  ? "recommended replenishment"
                  : "no additional cases needed"}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.08em] text-[#A09890]">
                Monitoring
              </div>

              <div className="mt-1 text-sm font-semibold text-[#343332]">
                {dc.skus_monitoring}{" "}
                {pluralize(
                  dc.skus_monitoring,
                  "SKU"
                )}
              </div>

              <div className="mt-1 text-xs text-[#8A8179]">
                {dc.skus_monitoring_projected_order >
                0
                  ? `${dc.skus_monitoring_projected_order} projected-order ${pluralize(
                      dc.skus_monitoring_projected_order,
                      "watch"
                    )}`
                  : "no immediate action"}
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

function CompactDcRow({
  dc,
  onClick,
  mode,
}: {
  dc: DistributionCenter
  onClick: () => void
  mode: "monitoring" | "healthy"
}) {
  const monitoring =
    mode === "monitoring"

  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full cursor-pointer items-center justify-between gap-4 border-b border-[#EEE5D8] px-1 py-4 text-left last:border-b-0"
    >
      <div className="flex min-w-0 items-center gap-3">
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
            monitoring
              ? "bg-[#F6F3FA] text-[#6E6683]"
              : "bg-[#F1F6F2] text-[#55735E]"
          }`}
        >
          {monitoring ? (
            <Truck className="h-4 w-4" />
          ) : (
            <PackageCheck className="h-4 w-4" />
          )}
        </div>

        <div>
          <div className="font-medium text-[#343332]">
            {dc.distributor} · {dc.dc}
          </div>

          <div className="mt-0.5 text-xs text-[#8A8179]">
            {monitoring
              ? `${dc.skus_monitoring} ${pluralize(
                  dc.skus_monitoring,
                  "SKU"
                )} monitoring`
              : `${dc.skus_healthy} healthy ${pluralize(
                  dc.skus_healthy,
                  "SKU"
                )} · ${dc.sku_count} total`}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden text-right sm:block">
          <div className="text-sm font-semibold text-[#343332]">
            {monitoring
              ? `${dc.skus_monitoring_projected_order} projected`
              : `${formatNumber(
                  dc.quantity_needed_cases
                )} cases`}
          </div>

          <div className="text-xs text-[#8A8179]">
            {monitoring
              ? "orders monitored"
              : "recommended"}
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
    useState<InventoryOverviewResponse | null>(
      null
    )

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const loadInventory = async () => {
    try {
      setLoading(true)
      setError(null)

      const params =
        new URLSearchParams()

      params.set(
        "org_id",
        "default_org"
      )

      const response = await fetch(
        `${API_BASE_URL}/inventory/overview?${params.toString()}`,
        {
          cache: "no-store",
        }
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
    monitoringDcs,
    reviewDcs,
    healthyDcs,
  } = useMemo(() => {
    const action: DistributionCenter[] =
      []
    const monitoring: DistributionCenter[] =
      []
    const review: DistributionCenter[] =
      []
    const healthy: DistributionCenter[] =
      []

    for (
      const dc of
        data?.distribution_centers ?? []
    ) {
      if (
        !dc.recommendation_complete ||
        dc.skus_needing_review > 0 ||
        dc.skus_projection_unavailable > 0
      ) {
        review.push(dc)
        continue
      }

      if (
        dc.skus_needing_action > 0
      ) {
        action.push(dc)
        continue
      }

      if (dc.skus_monitoring > 0) {
        monitoring.push(dc)
        continue
      }

      healthy.push(dc)
    }

    return {
      actionDcs: action,
      monitoringDcs: monitoring,
      reviewDcs: review,
      healthyDcs: healthy,
    }
  }, [data])

  const openDc = (
    dc: DistributionCenter
  ) => {
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
                  Inventory planning
                  could not load
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
            See where inventory needs
            action and where SKUba is
            monitoring future supply.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <SummaryCard
            icon={
              <AlertTriangle className="h-5 w-5" />
            }
            value={formatNumber(
              data.summary
                .dcs_needing_action
            )}
            label="DCs need action"
            detail="Locations with active inventory interventions"
          />

          <SummaryCard
            icon={
              <Boxes className="h-5 w-5" />
            }
            value={formatNumber(
              data.summary
                .known_recommended_cases
            )}
            label="Cases recommended"
            detail="Active new-order recommendations"
          />

          <SummaryCard
            icon={
              <Truck className="h-5 w-5" />
            }
            value={formatNumber(
              data.summary.dcs_monitoring
            )}
            label="DCs monitoring"
            detail="Locations with inventory being watched"
          />

          <SummaryCard
            icon={
              <CircleAlert className="h-5 w-5" />
            }
            value={formatNumber(
              data.summary
                .dcs_with_projection_unavailable
            )}
            label="Projection unavailable"
            detail="Locations with relevant inventory but unavailable projection"
          />

          <SummaryCard
            icon={
              <CircleAlert className="h-5 w-5" />
            }
            value={formatNumber(
              data.summary
                .dcs_needing_review
            )}
            label="DCs need review"
            detail="Locations with incomplete recommendations"
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
                  Locations with active
                  inventory interventions.
                </div>
              </div>

              <div className="text-xs font-medium text-[#A09890]">
                {actionDcs.length}{" "}
                {pluralize(
                  actionDcs.length,
                  "location"
                )}
              </div>
            </div>

            <div className="space-y-3">
              {actionDcs.length > 0 ? (
                actionDcs.map((dc) => (
                  <DcCard
                    key={`${dc.distributor}-${dc.dc}`}
                    dc={dc}
                    onClick={() =>
                      openDc(dc)
                    }
                  />
                ))
              ) : (
                <div className="rounded-[26px] border border-[#DDE7DF] bg-[#F7FBF8] p-6">
                  <div className="font-semibold text-[#55735E]">
                    No inventory actions
                    right now
                  </div>
                </div>
              )}
            </div>
          </section>

          <section>
            <div className="mb-4">
              <div className="text-lg font-semibold tracking-[-0.02em] text-[#343332]">
                Needs review
              </div>

              <div className="mt-1 text-sm text-[#8A8179]">
                Locations with unavailable
                or incomplete projections.
              </div>
            </div>

            <div className="overflow-hidden rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] shadow-sm">
              {reviewDcs.length > 0 ? (
                reviewDcs.map((dc) => (
                  <button
                    type="button"
                    key={`${dc.distributor}-${dc.dc}`}
                    onClick={() =>
                      openDc(dc)
                    }
                    className="group w-full cursor-pointer border-b border-[#EEE5D8] p-4 text-left last:border-b-0 hover:bg-[#FCFAF6]"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-[#343332]">
                          {dc.distributor} ·{" "}
                          {dc.dc}
                        </div>

                        <div className="mt-2 text-xs leading-5 text-[#8A8179]">
                          {
                            dc.skus_projection_unavailable
                          }{" "}
                          projection unavailable ·{" "}
                          {
                            dc.skus_needing_review
                          }{" "}
                          need review
                        </div>
                      </div>

                      <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-[#A59C93]" />
                    </div>
                  </button>
                ))
              ) : (
                <div className="p-5 text-sm text-[#8A8179]">
                  No locations currently
                  need review.
                </div>
              )}
            </div>
          </section>
        </div>

        {monitoringDcs.length > 0 && (
          <section>
            <div className="mb-4">
              <div className="text-lg font-semibold text-[#343332]">
                Monitoring
              </div>

              <div className="mt-1 text-sm text-[#8A8179]">
                No action recommended yet.
              </div>
            </div>

            <div className="rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] px-5 shadow-sm">
              {monitoringDcs.map((dc) => (
                <CompactDcRow
                  key={`${dc.distributor}-${dc.dc}`}
                  dc={dc}
                  mode="monitoring"
                  onClick={() =>
                    openDc(dc)
                  }
                />
              ))}
            </div>
          </section>
        )}

        <section>
          <div className="mb-4">
            <div className="text-lg font-semibold text-[#343332]">
              Healthy locations
            </div>
          </div>

          <div className="rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] px-5 shadow-sm">
            {healthyDcs.length > 0 ? (
              healthyDcs.map((dc) => (
                <CompactDcRow
                  key={`${dc.distributor}-${dc.dc}`}
                  dc={dc}
                  mode="healthy"
                  onClick={() =>
                    openDc(dc)
                  }
                />
              ))
            ) : (
              <div className="py-5 text-sm text-[#8A8179]">
                No healthy locations to
                show.
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}