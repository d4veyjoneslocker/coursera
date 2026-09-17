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
} from "lucide-react"

import {
  Card,
  CardContent,
} from "@/components/ui/card"
import DcStoreMap from "@/components/inventory/DcStoreMap"
import {
  InventoryAssessment,
  InventoryOutlook,
} from "@/components/inventory/InventoryOutlook"

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
  | "overview"
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


function SkuCard({
  sku,
}: {
  sku: SkuRow
}) {
  const [expanded, setExpanded] =
    useState(false)

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

  return (
    <div
      className="overflow-hidden rounded-[24px] border transition"
      style={{
        background:
          theme.softSurface,
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
        className="w-full p-5 text-left"
        aria-expanded={expanded}
      >
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <div
                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
                style={{
                  background:
                    "#F2EDE5",
                  color:
                    theme.accent,
                }}
              >
                <Box className="h-5 w-5" />
              </div>

              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <div
                    className="font-semibold"
                    style={{
                      color:
                        theme.charcoal,
                    }}
                  >
                    {sku.product_name}
                  </div>
                </div>

                <div
                  className="mt-0.5 text-xs"
                  style={{
                    color:
                      theme.brown,
                  }}
                >
                  {sku.sku}

                  {sku.units_per_case !=
                  null
                    ? ` · ${formatNumber(
                        sku.units_per_case
                      )} units / case`
                    : ""}
                </div>

                <div className="mt-2 flex flex-wrap gap-2">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-semibold ${getStatusClasses(
                      sku.inventory_status as InventoryStatus
                    )}`}
                  >
                    {getStatusLabel(
                      sku.inventory_status as InventoryStatus
                    )}
                  </span>

                  {sku.summary.active_intervention_types.map(
                    (action) => (
                      <span
                        key={action}
                        className="inline-flex rounded-full border border-[#E5DDD0] bg-white px-2.5 py-1 text-[10px] font-semibold text-[#705C4F]"
                      >
                        {actionLabel(
                          action
                        )}
                      </span>
                    )
                  )}
                </div>
              </div>
            </div>

            <div className="lg:text-right">
              <div
                className="text-[10px] font-semibold uppercase tracking-[0.12em]"
                style={{
                  color:
                    theme.brown,
                }}
              >
                Recommended
              </div>

              <div
                className="mt-1 text-2xl font-semibold"
                style={{
                  color:
                    theme.charcoal,
                }}
              >
                {sku.summary
                  .recommended_cases > 0
                  ? `${formatNumber(
                      sku.summary
                        .recommended_cases
                    )} cases`
                  : "No new order"}
              </div>

              {primaryOrder
                ?.order_by_date && (
                <div
                  className="mt-1 text-xs font-semibold"
                  style={{
                    color:
                      theme.coralDark,
                  }}
                >
                  {orderIsPastDue
                    ? "ORDER ASAP"
                    : `Order by ${formatDate(
                        primaryOrder.order_by_date
                      )}`}
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
            {sku.estimated_weeks_on_hand !=
              null && (
              <div>
                <div
                  className="text-[10px] font-semibold uppercase tracking-[0.12em]"
                  style={{
                    color: theme.brown,
                  }}
                >
                  Current coverage
                </div>

                <div
                  className="mt-1 text-lg font-semibold"
                  style={{
                    color: theme.charcoal,
                  }}
                >
                  {formatNumber(
                    sku.estimated_weeks_on_hand,
                    1
                  )}{" "}
                  WOH
                </div>
              </div>
            )}

            {sku.cases_per_week !=
              null && (
              <div>
                <div
                  className="text-[10px] font-semibold uppercase tracking-[0.12em]"
                  style={{
                    color: theme.brown,
                  }}
                >
                  Weekly velocity
                </div>

                <div
                  className="mt-1 text-lg font-semibold"
                  style={{
                    color: theme.charcoal,
                  }}
                >
                  {formatNumber(
                    sku.cases_per_week,
                    1
                  )}{" "}
                  cs/wk
                </div>
              </div>
            )}

            <div
              className="ml-auto flex items-center gap-1 text-xs font-medium"
              style={{
                color: theme.brown,
              }}
            >
              {expanded
                ? "Hide details"
                : "View inventory plan"}

              <ChevronDown
                className={`h-4 w-4 transition-transform duration-200 ${
                  expanded
                    ? "rotate-180"
                    : ""
                }`}
              />
            </div>
          </div>
        </div>
      </button>

      {expanded && (
        <div
          className="border-t px-5 pb-6 pt-5 md:px-6"
          style={{
            borderColor:
              theme.softLine,
            background:
              theme.surface,
          }}
        >
          <InventoryOutlook
            data={sku}
            accentColor={
              theme.accent
            }
            theme={{
              surface:
                theme.surface,
              line: theme.line,
              accent_color:
                theme.accent,
              charcoal:
                theme.charcoal,
            }}
          />
        </div>
      )}
    </div>
  )
}

export default function DistributionCenterDetailPage() {
  const params = useParams()

  const distributor = String(
    params.distributor ?? ""
  ).toUpperCase()

  const dcCode = String(
    params.dc ?? ""
  ).toUpperCase()

  const [data, setData] =
    useState<DcDetail | null>(null)

  const [activeTab, setActiveTab] =
    useState<Tab>("overview")

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
            org_id:
              "default_org",
            distributor,
            dc: dcCode,
          })

        const response =
          await fetch(
            `${API_BASE_URL}/inventory/dc-detail?${query.toString()}`,
            {
              signal:
                controller.signal,
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

        setData(payload)
      } catch (err) {
        if (
          err instanceof
            DOMException &&
          err.name === "AbortError"
        ) {
          return
        }

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load distribution center."
        )
      } finally {
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
            <CardContent className="flex min-h-[360px] items-center justify-center">
              <div
                className="flex items-center gap-3 text-sm font-medium"
                style={{
                  color:
                    theme.brown,
                }}
              >
                <RefreshCw className="h-4 w-4 animate-spin" />
                Loading distribution
                center…
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
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
              "overview",
              "Overview",
            ],
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
          "overview" && (
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <MetricBlock
                label="Needs action"
                value={formatNumber(
                  data.skus_needing_action
                )}
                secondary={`of ${data.sku_count} SKUs`}
                icon={
                  <AlertTriangle className="h-4 w-4" />
                }
              />

              <MetricBlock
                label="Monitoring"
                value={formatNumber(
                  data.skus_monitoring
                )}
                secondary="No immediate action required"
                icon={
                  <Clock3 className="h-4 w-4" />
                }
              />

              <MetricBlock
                label="Cases recommended"
                value={formatNumber(
                  data.quantity_needed_cases
                )}
                secondary="Across active new-order recommendations"
                icon={
                  <Box className="h-4 w-4" />
                }
              />

              <MetricBlock
                label="Expedite"
                value={formatNumber(
                  data.skus_to_expedite
                )}
                secondary={`${data.skus_needing_new_order} new-order ${data.skus_needing_new_order === 1 ? "SKU" : "SKUs"}`}
                icon={
                  <PackageCheck className="h-4 w-4" />
                }
              />
            </div>

            <Card
              className="overflow-hidden rounded-[28px] border shadow-sm"
              style={{
                background:
                  theme.surface,
                borderColor:
                  theme.line,
              }}
            >
              <CardContent className="p-0">
                <div className="grid lg:grid-cols-[1.1fr_0.9fr]">
                  <div
                    className="p-6 md:p-7 lg:border-r"
                    style={{
                      borderColor:
                        theme.line,
                    }}
                  >
                    <div className="mb-5">
                      <div
                        className="text-xs font-semibold uppercase tracking-[0.14em]"
                        style={{
                          color:
                            theme.accent,
                        }}
                      >
                        Inventory plan
                      </div>

                      <h2
                        className="mt-1 text-xl font-semibold"
                        style={{
                          color:
                            theme.charcoal,
                        }}
                      >
                        What needs
                        attention
                      </h2>
                    </div>

                    {actionSkus.length >
                    0 ? (
                      <div className="space-y-3">
                        {actionSkus.map(
                          (sku) => (
                            <div
                              key={
                                sku.sku
                              }
                              className="rounded-[20px] border px-4 py-4"
                              style={{
                                background:
                                  "#FBF2EE",
                                borderColor:
                                  "#F0D9D0",
                              }}
                            >
                              <div className="flex items-start justify-between gap-4">
                                <div className="min-w-0">
                                  <div
                                    className="font-semibold"
                                    style={{
                                      color:
                                        theme.charcoal,
                                    }}
                                  >
                                    {
                                      sku.product_name
                                    }
                                  </div>

                                  <div
                                    className="mt-1 text-sm leading-6"
                                    style={{
                                      color:
                                        theme.brown,
                                    }}
                                  >
                                    {sku.narrative ||
                                      "Inventory action recommended."}
                                  </div>

                                  <div className="mt-2 flex flex-wrap gap-2">
                                    {sku.summary.active_intervention_types.map(
                                      (
                                        action
                                      ) => (
                                        <span
                                          key={
                                            action
                                          }
                                          className="rounded-full border border-[#E5DDD0] bg-white px-2 py-1 text-[10px] font-semibold text-[#705C4F]"
                                        >
                                          {actionLabel(
                                            action
                                          )}
                                        </span>
                                      )
                                    )}
                                  </div>
                                </div>

                                <div className="shrink-0 text-right">
                                  <div
                                    className="text-xl font-semibold"
                                    style={{
                                      color:
                                        theme.charcoal,
                                    }}
                                  >
                                    {formatNumber(
                                      sku
                                        .summary
                                        .recommended_cases
                                    )}{" "}
                                    cs
                                  </div>
                                </div>
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    ) : (
                      <div className="rounded-[22px] border border-[#CFE2D6] bg-[#F1F8F3] p-5">
                        <div className="flex items-start gap-3">
                          <PackageCheck className="mt-0.5 h-5 w-5 text-[#55735E]" />

                          <div>
                            <div className="font-semibold text-[#55735E]">
                              No inventory
                              action required
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {monitoringSkus.length >
                      0 && (
                      <div className="mt-5">
                        <div
                          className="mb-3 text-[11px] font-semibold uppercase tracking-[0.13em]"
                          style={{
                            color:
                              theme.brown,
                          }}
                        >
                          Monitoring
                        </div>

                        <div className="space-y-2">
                          {monitoringSkus.map(
                            (sku) => (
                              <div
                                key={
                                  sku.sku
                                }
                                className="rounded-[18px] border px-4 py-3"
                                style={{
                                  background:
                                    "#FFF8E8",
                                  borderColor:
                                    "#E8D5B5",
                                }}
                              >
                                <div className="font-semibold text-[#343332]">
                                  {
                                    sku.product_name
                                  }
                                </div>

                                {sku.narrative && (
                                  <div className="mt-1 text-sm text-[#705C4F]">
                                    {
                                      sku.narrative
                                    }
                                  </div>
                                )}
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col p-6 md:p-7">
                    <div className="mb-4 flex items-start justify-between">
                      <div>
                        <div
                          className="text-xs font-semibold uppercase tracking-[0.14em]"
                          style={{
                            color:
                              theme.accent,
                          }}
                        >
                          Downstream demand
                        </div>

                        <h2
                          className="mt-1 text-xl font-semibold"
                          style={{
                            color:
                              theme.charcoal,
                          }}
                        >
                          Stores served
                        </h2>
                      </div>

                      <MapPin
                        className="h-5 w-5"
                        style={{
                          color:
                            theme.accent,
                        }}
                      />
                    </div>

                    <DcStoreMap
                      dcCode={
                        data.dc
                      }
                      dcName={
                        data.dc_name
                      }
                      dcLatitude={
                        data.dc_latitude
                      }
                      dcLongitude={
                        data.dc_longitude
                      }
                      stores={
                        data.stores
                      }
                    />

                    <div className="mt-4 grid grid-cols-3 gap-3">
                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#705C4F]">
                          Stores
                        </div>

                        <div className="mt-1 text-2xl font-semibold text-[#343332]">
                          {formatNumber(
                            data.active_store_count
                          )}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#705C4F]">
                          Action SKUs
                        </div>

                        <div className="mt-1 text-2xl font-semibold text-[#343332]">
                          {formatNumber(
                            data.skus_needing_action
                          )}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#705C4F]">
                          Recommended
                        </div>

                        <div className="mt-1 text-2xl font-semibold text-[#343332]">
                          {formatNumber(
                            data.quantity_needed_cases
                          )}
                        </div>

                        <div className="text-[11px] text-[#705C4F]">
                          cases
                        </div>
                      </div>
                    </div>

                    <button
                      className="mt-5 inline-flex w-fit items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-white"
                      style={{
                        background:
                          theme.charcoal,
                      }}
                    >
                      <Store className="h-4 w-4" />
                      Add Stores
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

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