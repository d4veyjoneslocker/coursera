"use client"

import {
  useEffect,
  useMemo,
  useState,
} from "react"
import { useParams } from "next/navigation"
import {
  AlertTriangle,
  ArrowDownToLine,
  Box,
  Building2,
  ChevronDown,
  CircleAlert,
  Clock3,
  MapPin,
  PackageCheck,
  RefreshCw,
  Store,
  Truck,
  Package
} from "lucide-react"

import {
  Card,
  CardContent,
} from "@/components/ui/card"
import DcStoreMap from "@/components/inventory/DcStoreMap"
import { useOrg } from "@/components/OrgContext"
import {
  InventoryAssessment,
  InventoryOutlook,
} from "@/components/inventory/InventoryOutlook"
import LoadingScreen from "@/components/LoadingScreen"

const theme = {
  primary: "#9A93B0",
  secondary: "#C58E82",
  accent: "#C8795A",
  charcoal: "#343332",
  brown: "#705C4F",
  cream: "#E9E2C8",
  bg: "#F6F2EA",
  line: "#E5DDD0",
  surface: "#FFFDF9",
  softSurface: "#FCFAF6",
  softLine: "#EEE5D8",
  coral: "#EE6A4C",
  coralDark: "#D9532F",
}

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
    "STRAWBERRY": {
      src: "/skus/smearcase-strawberry.png",
      scale: 1.0,
    },
    "PEANUT BUTTER": {
      src: "/skus/smearcase-peanut-butter.png",
      scale: 0.92,
    },
  }

type InventoryStatus =
  | "action"
  | "monitor"
  | "healthy"
  | "projection_unavailable"

type SkuRow = InventoryAssessment

type StoreRow = {
  coded_customer: string | null
  chain: string | null
  channel: string | null
  state: string | null
  latitude: number | null
  longitude: number | null
}

type DcDetail = {
  distributor: string
  dc: string
  dc_name: string
  dc_latitude: number | null
  dc_longitude: number | null

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

  active_store_count: number

  skus: SkuRow[]
  stores: StoreRow[]
}

type Tab =
  | "inventory"
  | "stores"

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000"

function formatNumber(
  value: number | null | undefined,
  digits = 0
) {
  if (
    value == null ||
    Number.isNaN(value)
  ) {
    return "—"
  }

  return value.toLocaleString(
    undefined,
    {
      minimumFractionDigits:
        digits,
      maximumFractionDigits:
        digits,
    }
  )
}

function formatDate(
  value: string | null | undefined
) {
  if (!value) return "—"

  const date = new Date(
    `${value}T00:00:00`
  )

  if (
    Number.isNaN(date.getTime())
  ) {
    return value
  }

  return date.toLocaleDateString(
    undefined,
    {
      month: "short",
      day: "numeric",
    }
  )
}

function dateValue(
  value: string | null | undefined
) {
  if (!value) {
    return Number.POSITIVE_INFINITY
  }

  return new Date(
    `${value}T00:00:00`
  ).getTime()
}

function getStatusLabel(
  status: InventoryStatus
) {
  if (status === "action") {
    return "Needs action"
  }

  if (status === "monitor") {
    return "Monitoring"
  }

  if (
    status ===
    "projection_unavailable"
  ) {
    return "Projection unavailable"
  }

  return "Healthy"
}

function getStatusClasses(
  status: InventoryStatus
) {
  if (status === "action") {
    return "border border-[#F0C8BE] bg-[#FFF1EC] text-[#B94A30]"
  }

  if (status === "monitor") {
    return "border border-[#E8D5B5] bg-[#FFF8E8] text-[#8A651F]"
  }

  if (
    status ===
    "projection_unavailable"
  ) {
    return "border border-[#DED8E8] bg-[#F5F2FA] text-[#6D6681]"
  }

  return "border border-[#CFE2D6] bg-[#F1F8F3] text-[#55735E]"
}

function actionLabel(
  action: string
) {
  if (action === "new_order") {
    return "New order"
  }

  if (action === "expedite_po") {
    return "Expedite PO"
  }

  if (
    action ===
    "monitor_projected_order"
  ) {
    return "Monitor projected order"
  }

  if (
    action ===
    "future_replenishment"
  ) {
    return "Future replenishment"
  }

  if (action === "review") {
    return "Review"
  }

  return action.replaceAll("_", " ")
}

function getPrimaryOrder(
  sku: SkuRow
) {
  const interventions =
    sku.breaches
      .map(
        (breach) =>
          breach.intervention
      )
      .filter(Boolean)

  return interventions.find(
    (intervention) =>
      intervention
        ?.intervention_type ===
      "new_order"
  )
}


function MetricBlock({
  label,
  value,
  secondary,
  icon,
}: {
  label: string
  value: string
  secondary?: string
  icon: React.ReactNode
}) {
  return (
    <div
      className="rounded-[22px] border px-4 py-4"
      style={{
        background:
          theme.softSurface,
        borderColor:
          theme.softLine,
      }}
    >
      <div className="mb-3 flex items-center gap-2">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-xl"
          style={{
            background: "#F3ECE6",
            color: theme.accent,
          }}
        >
          {icon}
        </div>

        <div
          className="text-[11px] font-semibold uppercase tracking-[0.13em]"
          style={{
            color: theme.brown,
          }}
        >
          {label}
        </div>
      </div>

      <div
        className="text-[30px] font-semibold tracking-tight"
        style={{
          color: theme.charcoal,
        }}
      >
        {value}
      </div>

      {secondary && (
        <div
          className="mt-1 text-sm"
          style={{
            color: theme.brown,
          }}
        >
          {secondary}
        </div>
      )}
    </div>
  )
}


function getOpenPoSummary(sku: SkuRow) {
  const events =
    sku.baseline?.confirmed_po_events?.filter(
      (event) =>
        (event.cases ?? 0) > 0 &&
        !event.is_stale &&
        event.receipt_date
    ) ?? []

  if (events.length === 0) {
    return null
  }

  const datedEvents = events
    .map((event) => ({
      ...event,
      displayDate: event.receipt_date,
    }))
    .sort(
      (a, b) =>
        dateValue(a.displayDate) -
        dateValue(b.displayDate)
    )

  const totalCases = events.reduce(
    (sum, event) => sum + (event.cases ?? 0),
    0
  )

  return {
    totalCases,
    expectedDate:
      datedEvents[0]?.displayDate ?? null,
  }
}

function SkuCard({
  sku,
  skuColor,
}: {
  sku: SkuRow
  skuColor: string
}) {
  const [expanded, setExpanded] =
    useState(false)

  const productImage = SKU_IMAGES[sku.sku]

  const primaryOrder =
    getPrimaryOrder(sku)

  const asOfDate =
    sku.as_of_date ??
    sku.baseline?.as_of_date

  const orderIsPastDue =
    Boolean(
      primaryOrder?.order_by_date &&
        asOfDate &&
        dateValue(
          primaryOrder.order_by_date
        ) < dateValue(asOfDate)
    )

  const openPo = getOpenPoSummary(sku)

  const expediteIntervention =
    sku.breaches
      .map(
        (breach) =>
          breach.intervention
      )
      .filter(Boolean)
      .find(
        (intervention) =>
          intervention
            ?.intervention_type ===
          "expedite_po"
      )

  const neededByDate =
    expediteIntervention
      ?.needed_by_date ??
    primaryOrder?.needed_by_date ??
    null

  const hasNewOrder =
    sku.summary.active_intervention_types.includes(
      "new_order"
    )

  const hasExpedite =
    sku.summary.active_intervention_types.includes(
      "expedite_po"
    )

  const coverage =
    sku.estimated_weeks_on_hand ?? 0

  const coveragePercent = Math.max(
    0,
    Math.min(100, (coverage / 5) * 100)
  )

  const recommendationTitle =
    sku.summary.recommended_cases > 0
      ? `Order ${formatNumber(
          sku.summary.recommended_cases
        )} cases`
      : hasExpedite
        ? "Follow up on PO"
        : "No new order"

  const recommendationTiming =
    sku.summary.recommended_cases > 0
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

  return (
    <div
      className="overflow-hidden rounded-[24px] border transition"
      style={{
        background: theme.softSurface,
        borderColor: expanded
          ? "#D9CFC1"
          : theme.softLine,
      }}
    >
      <button
        type="button"
        onClick={() =>
          setExpanded(
            (current) => !current
          )
        }
        className="w-full text-left"
        aria-expanded={expanded}
      >
                <div className="grid overflow-hidden lg:grid-cols-[190px_minmax(0,1fr)_1px_310px] lg:items-stretch">
                  {/* PRODUCT IMAGE */}
                    <div
                      className="flex min-h-[210px] items-center justify-center overflow-hidden p-3"
                      style={{
                        backgroundColor: `${skuColor}0D`,
                      }}
                    >
                      {productImage ? (
                        <img
                          src={productImage.src}
                          alt={sku.product_name ?? sku.sku}
                          className="h-[180px] w-[170px] object-contain"
                          style={{
                            transform: `translateX(${productImage.x ?? 0}px) scale(${productImage.scale})`,
                          }}
                        />
                      ) : (
                        <Package
                          className="h-8 w-8"
                          style={{
                            color: skuColor,
                          }}
                        />
                      )}
                    </div>
                  {/* PRODUCT + INVENTORY STATE */}
                  <div className="flex min-w-0 items-center px-8 py-6">
                    <div className="relative w-full">
                      {/* PRODUCT NAME */}
                      <div
                        className="text-[17px] font-bold tracking-[-0.015em]"
                        style={{
                          color: theme.charcoal,
                        }}
                      >
                        {sku.product_name}
                      </div>

                      {/* STATUS */}
                      <span
                        className="absolute right-0 top-[-3px] inline-flex rounded-full border px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.14em]"
                        style={{
                          color: theme.coralDark,
                          borderColor: "#F2B9AA",
                          background: "#FFF7F3",
                        }}
                      >
                        {getStatusLabel(
                          sku.inventory_status as InventoryStatus
                        )}
                      </span>

                      {/* CURRENT STATE → OPEN PO */}
                      <div className="mt-7 grid grid-cols-[minmax(280px,0.75fr)_54px_minmax(250px,1fr)] items-center gap-4">
                        {/* CURRENT COVERAGE */}
                        <div>
                          <div className="flex items-baseline gap-2">
                            <div
                              className="text-[38px] font-bold leading-none tracking-[-0.045em]"
                              style={{
                                color: theme.charcoal,
                              }}
                            >
                              {sku.estimated_weeks_on_hand != null
                                ? formatNumber(
                                    sku.estimated_weeks_on_hand,
                                    1
                                  )
                                : "—"}
                            </div>

                            <div
                              className="text-[23px] font-semibold tracking-[-0.025em]"
                              style={{
                                color: theme.charcoal,
                              }}
                            >
                              WOH
                            </div>
                          </div>

                          <div
                            className="mt-2 text-[15px] font-medium"
                            style={{
                              color: theme.brown,
                            }}
                          >
                            {sku.cases_per_week != null
                              ? `${formatNumber(
                                  sku.cases_per_week,
                                  1
                                )} cases / week`
                              : "Velocity unavailable"}
                          </div>

                          {sku.estimated_weeks_on_hand != null && (
                            <div className="mt-3 max-w-[285px]">
                              <div className="relative h-[9px] rounded-full bg-[#E8E1D7]">
                                <div
                                  className="absolute inset-y-0 left-0 rounded-full"
                                  style={{
                                    width: `${coveragePercent}%`,
                                    background: skuColor,
                                  }}
                                />

                                <div
                                  className="absolute -bottom-[5px] -top-[5px] w-px"
                                  style={{
                                    left: "60%",
                                    background: "#9C8F80",
                                  }}
                                />
                              </div>

                              <div
                                className="relative mt-2 h-4 text-[11px] font-medium"
                                style={{
                                  color: "#A09386",
                                }}
                              >
                                <span className="absolute left-[60%] -translate-x-1/2 whitespace-nowrap">
                                  3 WOH floor
                                </span>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* FLOW ARROW */}
                        <div
                          className="flex items-center justify-center text-[36px] font-light"
                          style={{
                            color: "#BBAE9F",
                          }}
                          aria-hidden="true"
                        >
                          →
                        </div>

                        {/* OPEN PO */}
                        <div>
                          <div
                            className="text-[10px] font-bold uppercase tracking-[0.2em]"
                            style={{
                              color: "#8C7D70",
                            }}
                          >
                            {openPo ? "Open PO" : "Open POs"}
                          </div>

                          {openPo ? (
                            <>
                              <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                                <span
                                  className="text-[18px] font-bold tracking-[-0.02em]"
                                  style={{
                                    color: theme.charcoal,
                                  }}
                                >
                                  +{formatNumber(
                                    openPo.totalCases
                                  )} cases
                                </span>

                                {openPo.expectedDate && (
                                  <span
                                    className="text-[14px] font-medium"
                                    style={{
                                      color: theme.brown,
                                    }}
                                  >
                                    Expected{" "}
                                    {formatDate(
                                      openPo.expectedDate
                                    )}
                                  </span>
                                )}
                              </div>

                              {hasExpedite ? (
                                <div
                                  className="mt-2 text-[11px] font-bold uppercase tracking-[0.13em]"
                                  style={{
                                    color: theme.coralDark,
                                  }}
                                >
                                  Not in time
                                  {neededByDate
                                    ? ` · Needed ${formatDate(
                                        neededByDate
                                      )}`
                                    : ""}
                                </div>
                              ) : hasNewOrder ? (
                                <div
                                  className="mt-2 text-[11px] font-bold uppercase tracking-[0.13em]"
                                  style={{
                                    color: theme.coralDark,
                                  }}
                                >
                                  Not enough
                                </div>
                              ) : null}
                            </>
                          ) : (
                            <div
                              className="mt-2 text-[17px] font-bold tracking-[-0.02em]"
                              style={{
                                color: theme.charcoal,
                              }}
                            >
                              No open POs
                            </div>
                          )}
                        </div>
                      </div>
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
                  <div className="flex min-w-0 flex-col justify-center px-8 py-6">
                    <div
                      className="text-[10px] font-bold uppercase tracking-[0.2em]"
                      style={{
                        color: "#7E7064",
                      }}
                    >
                      SKUba recommends
                    </div>

                    <div
                      className="mt-3 text-[31px] font-bold leading-[1.05] tracking-[-0.045em]"
                      style={{
                        color: skuColor,
                      }}
                    >
                      {recommendationTitle}
                    </div>

                    {recommendationTiming && (
                      <div
                        className="mt-2 text-[12px] font-semibold uppercase tracking-[0.08em]"
                        style={{
                          color: theme.brown,
                        }}
                      >
                        {recommendationTiming}
                      </div>
                    )}

                    <div
                      className="mt-6 flex items-center gap-3 text-[13px] font-bold"
                      style={{
                        color: theme.charcoal,
                      }}
                    >
                      {expanded
                        ? "Hide inventory plan"
                        : "View inventory plan"}

                      <span
                        className="text-[18px] font-normal leading-none"
                        aria-hidden="true"
                      >
                        →
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
          <InventoryOutlook
            data={sku}
            accentColor={skuColor}
            theme={{
              surface: theme.surface,
              line: theme.line,
              accent_color: skuColor,
              charcoal: theme.charcoal,
            }}
          />
        </div>
      )}
    </div>
  )
}

export default function DistributionCenterDetailPage() {
  const params = useParams()
  const { skuColors } = useOrg()

  const distributor = String(
    params.distributor ?? ""
  ).toUpperCase()

  const dcCode = String(
    params.dc ?? ""
  ).toUpperCase()

  const [data, setData] =
    useState<DcDetail | null>(null)

  const [activeTab, setActiveTab] =
    useState<Tab>("inventory")

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  useEffect(() => {
    if (
      !distributor ||
      !dcCode
    ) {
      return
    }

    const controller =
      new AbortController()

    async function loadDc() {
      try {
        setLoading(true)
        setError(null)

        const query =
          new URLSearchParams({
            org_id: "default_org",
            distributor,
            dc: dcCode,
          })

        const response =
          await fetch(
            `${API_BASE_URL}/inventory/dc-detail?${query.toString()}`,
            {
              signal: controller.signal,
              cache: "no-store",
            }
          )

        if (!response.ok) {
          const body =
            await response
              .json()
              .catch(() => null)

          throw new Error(
            body?.detail ??
              `Failed to load ${distributor} ${dcCode}`
          )
        }

        const payload: DcDetail =
          await response.json()

        if (controller.signal.aborted) {
          return
        }

        setData(payload)
        setLoading(false)
      } catch (err) {
        if (controller.signal.aborted) {
          return
        }

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load distribution center."
        )
        setLoading(false)
      }
    }

    loadDc()

    return () =>
      controller.abort()
  }, [distributor, dcCode])

  const sortedSkus =
    useMemo(() => {
      if (!data) return []

      const statusRank: Record<
        InventoryStatus,
        number
      > = {
        action: 0,
        monitor: 1,
        projection_unavailable: 2,
        healthy: 3,
      }

      return [...data.skus].sort(
        (a, b) =>
          (statusRank[
            a.inventory_status as InventoryStatus
          ] ?? 99) -
          (statusRank[
            b.inventory_status as InventoryStatus
          ] ?? 99)
      )
    }, [data])

  if (loading) {
      return <LoadingScreen mode="dc-detail" />
    }

  if (error || !data) {
    return (
      <div
        className="min-h-screen px-6 py-10"
        style={{
          background: theme.bg,
        }}
      >
        <div className="mx-auto max-w-[1500px]">
          <Card
            className="rounded-[28px] border shadow-sm"
            style={{
              background:
                theme.surface,
              borderColor:
                theme.line,
            }}
          >
            <CardContent className="p-8">
              <div className="flex items-center gap-3">
                <AlertTriangle
                  className="h-5 w-5"
                  style={{
                    color:
                      theme.coral,
                  }}
                />

                <div
                  className="font-medium"
                  style={{
                    color:
                      theme.charcoal,
                  }}
                >
                  {error ??
                    "Distribution center not found."}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  const dcStatus: InventoryStatus =
    data.skus_needing_action > 0
      ? "action"
      : data.skus_monitoring > 0
        ? "monitor"
        : data.skus_projection_unavailable >
            0
          ? "projection_unavailable"
          : "healthy"

  const actionSkus =
    sortedSkus.filter(
      (sku) =>
        sku.inventory_status ===
        "action"
    )

  const monitoringSkus =
    sortedSkus.filter(
      (sku) =>
        sku.inventory_status ===
        "monitor"
    )

  return (
    <div
      className="min-h-screen px-5 py-7 md:px-8 md:py-9"
      style={{
        background: theme.bg,
      }}
    >
      <div className="mx-auto max-w-[1500px] space-y-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div
              className="mb-2 text-xs font-semibold uppercase tracking-[0.15em]"
              style={{
                color: theme.accent,
              }}
            >
              {data.distributor} ·{" "}
              {data.dc}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <h1
                className="text-3xl font-semibold tracking-tight md:text-4xl"
                style={{
                  color:
                    theme.charcoal,
                }}
              >
                {data.dc_name}
              </h1>

              <span
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${getStatusClasses(
                  dcStatus
                )}`}
              >
                {getStatusLabel(
                  dcStatus
                )}
              </span>
            </div>

            <div
              className="mt-2 text-sm"
              style={{
                color: theme.brown,
              }}
            >
              SKU-level inventory
              planning and downstream
              demand
            </div>
          </div>

          <button
            className="inline-flex items-center justify-center gap-2 rounded-2xl border px-4 py-2.5 text-sm font-medium transition hover:bg-white"
            style={{
              color: theme.brown,
              borderColor:
                theme.line,
              background:
                theme.surface,
            }}
          >
            <ArrowDownToLine className="h-4 w-4" />
            Export
          </button>
        </div>

        <div className="flex gap-2">
          {[
            [
              "inventory",
              "Inventory Snapshot",
            ],
            ["stores", "Stores"],
          ].map(
            ([value, label]) => {
              const selected =
                activeTab === value

              return (
                <button
                  key={value}
                  onClick={() =>
                    setActiveTab(
                      value as Tab
                    )
                  }
                  className="rounded-full px-4 py-2 text-sm font-medium transition"
                  style={{
                    background:
                      selected
                        ? theme.charcoal
                        : "transparent",
                    color: selected
                      ? "#FFFFFF"
                      : theme.brown,
                  }}
                >
                  {label}
                </button>
              )
            }
          )}
        </div>


        {activeTab ===
          "inventory" && (
          <Card
            className="rounded-[28px] border shadow-sm"
            style={{
              background:
                theme.surface,
              borderColor:
                theme.line,
            }}
          >
            <CardContent className="p-6 md:p-7">
              <div className="mb-5">
                <div
                  className="text-xs font-semibold uppercase tracking-[0.14em]"
                  style={{
                    color:
                      theme.accent,
                  }}
                >
                  Inventory snapshot
                </div>

                <h2 className="mt-1 text-xl font-semibold text-[#343332]">
                  {data.sku_count} SKUs
                  at {data.dc}
                </h2>
              </div>

              <div className="space-y-3">
                {sortedSkus.map(
                  (sku) => (
                    <SkuCard
                      key={
                        sku.sku
                      }
                      sku={sku}
                      skuColor={
                        skuColors[sku.sku] ??
                        skuColors[sku.product_name] ??
                        theme.accent
                      }
                    />
                  )
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === "stores" && (
          <Card
            className="rounded-[28px] border shadow-sm"
            style={{
              background:
                theme.surface,
              borderColor:
                theme.line,
            }}
          >
            <CardContent className="p-6 md:p-7">
              <div className="mb-5">
                <div
                  className="text-xs font-semibold uppercase tracking-[0.14em]"
                  style={{
                    color:
                      theme.accent,
                  }}
                >
                  Downstream network
                </div>

                <h2 className="mt-1 text-xl font-semibold text-[#343332]">
                  {formatNumber(
                    data.active_store_count
                  )}{" "}
                  active stores
                </h2>
              </div>

              <div className="mb-5">
                <DcStoreMap
                  dcCode={data.dc}
                  dcName={
                    data.dc_name
                  }
                  dcLatitude={
                    data.dc_latitude
                  }
                  dcLongitude={
                    data.dc_longitude
                  }
                  stores={data.stores}
                />
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {data.stores.map(
                  (
                    store,
                    index
                  ) => (
                    <div
                      key={`${store.coded_customer}-${index}`}
                      className="rounded-[20px] border px-4 py-4"
                      style={{
                        background:
                          theme.softSurface,
                        borderColor:
                          theme.softLine,
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
                          style={{
                            background:
                              "#F2EDE5",
                            color:
                              theme.accent,
                          }}
                        >
                          <Building2 className="h-4 w-4" />
                        </div>

                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-[#343332]">
                            {store.coded_customer ??
                              "Unnamed store"}
                          </div>

                          <div className="mt-1 text-xs text-[#705C4F]">
                            {[
                              store.chain,
                              store.channel,
                              store.state,
                            ]
                              .filter(
                                Boolean
                              )
                              .join(
                                " · "
                              )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}