"use client"

import {
  useEffect,
  useMemo,
  useState,
} from "react"
import { useRouter } from "next/navigation"
import {
  Boxes,
  ChevronRight,
  Clock3,
  Package,
  RefreshCw,
  Search,
  Truck,
  Warehouse,
} from "lucide-react"

import {
  Card,
  CardContent,
} from "@/components/ui/card"

import DcNetworkMap, {
  type MapDistributionCenter,
} from "@/components/inventory/DcNetworkMap"

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
}

const inventoryStateColors = {
  oos: "#D95F4B",
  low: "#EE8B68",
  watch: "#D9AD4E",
  healthy: "#6F9D7C",
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000"

type DcRow = {
  as_of_date: string
  report_date: string | null
  distributor: string
  dc: string
  quantity_on_hand_cases: number
  quantity_on_po_cases: number
  velocity_cases_per_week: number
  weeks_on_hand: number | null
  sku_count: number

  skus_oos: number
  skus_below_3_woh: number
  skus_3_to_4_woh: number
  skus_4_plus_woh: number
  skus_woh_unavailable: number

  oos_events_l6m: number
  oos_history_complete: boolean
  planning_lead_time_days: number | null
  planning_lead_time_source: string | null
}

type DcNetworkPayload = {
  as_of_date: string | null
  summary: {
    quantity_on_hand_cases: number
    quantity_on_po_cases: number
    network_woh: number | null
    active_dc_count: number
    sku_count: number
    oos_events_l6m: number
  }
  distribution_centers: DcRow[]

  map_data: MapDistributionCenter[]
}

type DistributorFilter =
  | "ALL"
  | "UNFI"
  | "KEHE"

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
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
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

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleDateString(
    undefined,
    {
      month: "short",
      day: "numeric",
      year: "numeric",
    }
  )
}

function formatReportDate(
  value: string | null | undefined
) {
  if (!value) return "—"

  const date = new Date(
    `${value}T00:00:00`
  )

  if (Number.isNaN(date.getTime())) {
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

function MetricCard({
  label,
  value,
  secondary,
  icon,
}: {
  label: string
  value: string
  secondary: string
  icon: React.ReactNode
}) {
  return (
    <Card
      className="rounded-[24px] border shadow-sm"
      style={{
        background: theme.surface,
        borderColor: theme.line,
      }}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div
              className="text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: theme.brown }}
            >
              {label}
            </div>

            <div
              className="mt-2 text-[31px] font-semibold tracking-[-0.04em]"
              style={{ color: theme.charcoal }}
            >
              {value}
            </div>

            <div
              className="mt-1 text-sm"
              style={{ color: theme.brown }}
            >
              {secondary}
            </div>
          </div>

          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl"
            style={{
              background: "#F3ECE6",
              color: theme.accent,
            }}
          >
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function DistributorBadge({
  distributor,
}: {
  distributor: string
}) {
  const isUnfi =
    distributor.toUpperCase() === "UNFI"

  return (
    <span
      className="inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em]"
      style={{
        background: isUnfi
          ? "#F3F0F7"
          : "#F8EFEA",
        borderColor: isUnfi
          ? "#DDD6E7"
          : "#E8D8CE",
        color: isUnfi
          ? "#6F6880"
          : "#8B6658",
      }}
    >
      {distributor}
    </span>
  )
}

function StateLabel({
  color,
  count,
  label,
}: {
  color: string
  count: number
  label: string
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="h-2.5 w-2.5 shrink-0 rounded-full"
        style={{ background: color }}
      />

      <span
        className="whitespace-nowrap text-xs font-semibold"
        style={{ color: theme.charcoal }}
      >
        {count} {count === 1 ? "SKU" : "SKUs"} · {label}
      </span>
    </div>
  )
}

function InventoryStateBar({
  row,
}: {
  row: DcRow
}) {
  const oos = row.skus_oos ?? 0
  const below = row.skus_below_3_woh ?? 0
  const middle = row.skus_3_to_4_woh ?? 0
  const above = row.skus_4_plus_woh ?? 0
  const unavailable =
    row.skus_woh_unavailable ?? 0

  const knownCount =
    oos + below + middle + above

  if (knownCount === 0) {
    return (
      <div
        className="text-xs font-semibold"
        style={{ color: theme.brown }}
      >
        WOH unavailable
      </div>
    )
  }

  const oosPct = (oos / knownCount) * 100
  const belowPct =
    (below / knownCount) * 100
  const middlePct =
    (middle / knownCount) * 100
  const abovePct =
    (above / knownCount) * 100

  return (
    <div className="min-w-[245px]">
      <div
        className="flex h-2.5 overflow-hidden rounded-full"
        style={{ background: "#EEE8DF" }}
      >
        {oos > 0 && (
          <div
            style={{
              width: `${oosPct}%`,
              background:
                inventoryStateColors.oos,
            }}
          />
        )}

        {below > 0 && (
          <div
            style={{
              width: `${belowPct}%`,
              background:
                inventoryStateColors.low,
            }}
          />
        )}

        {middle > 0 && (
          <div
            style={{
              width: `${middlePct}%`,
              background:
                inventoryStateColors.watch,
            }}
          />
        )}

        {above > 0 && (
          <div
            style={{
              width: `${abovePct}%`,
              background:
                inventoryStateColors.healthy,
            }}
          />
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-8 gap-y-2.5">
        {oos > 0 && (
            <StateLabel
            color={inventoryStateColors.oos}
            count={oos}
            label="OOS"
            />
        )}

        {below > 0 && (
            <StateLabel
            color={inventoryStateColors.low}
            count={below}
            label="<3 WOH"
            />
        )}

        {middle > 0 && (
            <StateLabel
            color={inventoryStateColors.watch}
            count={middle}
            label="3–4 WOH"
            />
        )}

        {above > 0 && (
            <StateLabel
            color={inventoryStateColors.healthy}
            count={above}
            label="4+ WOH"
            />
        )}

        {unavailable > 0 && (
            <StateLabel
            color="#9A8E82"
            count={unavailable}
            label="WOH unavailable"
            />
        )}
        </div>
    </div>
  )
}

export default function DcNetworkPage() {
  const router = useRouter()

  const [data, setData] =
    useState<DcNetworkPayload | null>(
      null
    )

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const [filter, setFilter] =
    useState<DistributorFilter>("ALL")

  const [search, setSearch] =
    useState("")

  useEffect(() => {
    const controller =
      new AbortController()

    async function loadNetwork() {
      try {
        setLoading(true)
        setError(null)

        const query =
          new URLSearchParams({
            org_id: "default_org",
          })

        const response =
          await fetch(
            `${API_BASE_URL}/inventory/dcs?${query.toString()}`,
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
              "Failed to load DC network."
          )
        }

        const payload: DcNetworkPayload =
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
            : "Failed to load DC network."
        )
        setLoading(false)
      }
    }

    loadNetwork()

    return () =>
      controller.abort()
  }, [])

  const visibleRows =
    useMemo(() => {
      if (!data) return []

      const searchValue =
        search.trim().toLowerCase()

      return data.distribution_centers
        .filter((row) => {
          if (
            filter !== "ALL" &&
            row.distributor.toUpperCase() !==
              filter
          ) {
            return false
          }

          if (!searchValue) {
            return true
          }

          return (
            row.dc
              .toLowerCase()
              .includes(searchValue) ||
            row.distributor
              .toLowerCase()
              .includes(searchValue)
          )
        })
        .sort((a, b) => {
          const distributorCompare =
            a.distributor.localeCompare(
              b.distributor
            )

          if (distributorCompare !== 0) {
            return distributorCompare
          }

          return a.dc.localeCompare(b.dc)
        })
    }, [data, filter, search])

const mapDistributionCenters =
  useMemo(() => {
    if (!data) return []

    return (data.map_data ?? []).map(
      (mapDc) => {
        const inventoryDc =
          data.distribution_centers.find(
            (row) =>
              row.distributor.toUpperCase() ===
                mapDc.distributor.toUpperCase() &&
              row.dc.toUpperCase() ===
                mapDc.dc.toUpperCase()
          )

        return {
          ...mapDc,
          ...(inventoryDc ?? {}),
        }
      }
    )
  }, [data])

  function openDc(row: DcRow) {
    router.push(
      `/inventory/${encodeURIComponent(
        row.distributor.toLowerCase()
      )}/${encodeURIComponent(
        row.dc.toLowerCase()
      )}`
    )
  }

  if (loading) {
    return <LoadingScreen mode="dc-network" />
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
              <div
                className="font-medium"
                style={{
                  color:
                    theme.charcoal,
                }}
              >
                {error ??
                  "DC network unavailable."}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

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
              Inventory · DCs
            </div>

            <h1
              className="text-3xl font-semibold tracking-tight md:text-4xl"
              style={{
                color:
                  theme.charcoal,
              }}
            >
              Distribution Centers
            </h1>

            <div
              className="mt-2 text-sm"
              style={{
                color: theme.brown,
              }}
            >
              A factual view of inventory
              across the network. No
              recommendations — just what
              is currently true.
            </div>
          </div>

          <div
            className="text-sm font-medium"
            style={{
              color: theme.brown,
            }}
          >
            As of{" "}
            {formatDate(
              data.as_of_date
            )}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Cases on hand"
            value={formatNumber(
              data.summary
                .quantity_on_hand_cases
            )}
            secondary="Physical inventory across the network"
            icon={
              <Boxes className="h-4 w-4" />
            }
          />

          <MetricCard
            label="Cases on open POs"
            value={formatNumber(
              data.summary
                .quantity_on_po_cases
            )}
            secondary="Currently open purchase orders"
            icon={
              <Truck className="h-4 w-4" />
            }
          />

          <MetricCard
            label="Network WOH"
            value={
              data.summary
                .network_woh != null
                ? `${formatNumber(
                    data.summary
                      .network_woh,
                    1
                  )}`
                : "—"
            }
            secondary="On-hand inventory at current velocity"
            icon={
              <Package className="h-4 w-4" />
            }
          />

          <MetricCard
            label="Active DCs"
            value={formatNumber(
              data.summary
                .active_dc_count
            )}
            secondary={`${formatNumber(
              data.summary.sku_count
            )} active DC-SKU combinations`}
            icon={
              <Warehouse className="h-4 w-4" />
            }
          />
        </div>

        <Card
            className="overflow-hidden rounded-[28px] border shadow-sm"
            style={{
                background: theme.surface,
                borderColor: theme.line,
            }}
            >
            <CardContent className="p-0">
                <div className="px-5 pt-5 pb-4">
                <div
                    className="text-xs font-semibold uppercase tracking-[0.14em]"
                    style={{
                    color: theme.accent,
                    }}
                >
                    Network map
                </div>

                <div
                    className="mt-1 text-lg font-semibold"
                    style={{
                    color: theme.charcoal,
                    }}
                >
                    Distribution footprint
                </div>

                <div
                    className="mt-1 text-sm"
                    style={{
                    color: theme.brown,
                    }}
                >
                    Distribution centers and the stores they service.
                </div>
                </div>

                <div className="px-5 pb-5">
                    <DcNetworkMap
                    distributionCenters={mapDistributionCenters}
                    />
                </div>
            </CardContent>
            </Card>

        <Card
          className="overflow-hidden rounded-[28px] border shadow-sm"
          style={{
            background: theme.surface,
            borderColor: theme.line,
          }}
        >
          <CardContent className="p-0">
            <div
              className="flex flex-col gap-3 border-b px-5 py-4 lg:flex-row lg:items-center lg:justify-between"
              style={{
                borderColor: theme.line,
              }}
            >
              <div>
                <div
                  className="text-xs font-semibold uppercase tracking-[0.14em]"
                  style={{
                    color:
                      theme.accent,
                  }}
                >
                  Network
                </div>

                <div
                  className="mt-1 text-lg font-semibold"
                  style={{
                    color:
                      theme.charcoal,
                  }}
                >
                  {visibleRows.length}{" "}
                  distribution{" "}
                  {visibleRows.length === 1
                    ? "center"
                    : "centers"}
                </div>
              </div>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <div
                  className="inline-flex w-fit rounded-full border p-1"
                  style={{
                    borderColor:
                      theme.line,
                    background:
                      theme.softSurface,
                  }}
                >
                  {(
                    [
                      "ALL",
                      "UNFI",
                      "KEHE",
                    ] as DistributorFilter[]
                  ).map((value) => {
                    const selected =
                      filter === value

                    return (
                      <button
                        key={value}
                        type="button"
                        onClick={() =>
                          setFilter(value)
                        }
                        className="rounded-full px-3.5 py-1.5 text-xs font-semibold transition"
                        style={{
                          background:
                            selected
                              ? theme.charcoal
                              : "transparent",
                          color:
                            selected
                              ? "#FFFFFF"
                              : theme.brown,
                        }}
                      >
                        {value === "ALL"
                          ? "All DCs"
                          : value}
                      </button>
                    )
                  })}
                </div>

                <div
                  className="flex min-w-[220px] items-center gap-2 rounded-2xl border px-3 py-2.5"
                  style={{
                    borderColor:
                      theme.line,
                    background:
                      theme.softSurface,
                  }}
                >
                  <Search
                    className="h-4 w-4 shrink-0"
                    style={{
                      color:
                        "#9B8E81",
                    }}
                  />

                  <input
                    value={search}
                    onChange={(event) =>
                      setSearch(
                        event.target
                          .value
                      )
                    }
                    placeholder="Search DC"
                    className="w-full bg-transparent text-sm outline-none placeholder:text-[#A99D91]"
                    style={{
                      color:
                        theme.charcoal,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <div className="min-w-[1120px]">
                <div
                  className="grid grid-cols-[1.4fr_0.75fr_0.75fr_0.7fr_0.8fr_0.75fr_1.45fr_34px] items-center gap-4 border-b px-5 py-3 text-[10px] font-bold uppercase tracking-[0.13em]"
                  style={{
                    borderColor:
                      theme.softLine,
                    color: "#8B7E72",
                    background:
                      theme.softSurface,
                  }}
                >
                  <div>
                    Distribution center
                  </div>
                  <div>On hand</div>
                  <div>Open PO</div>
                  <div>WOH</div>
                  <div>Velocity</div>
                  <div>OOS · L6M</div>
                  <div>
                    SKU inventory state
                  </div>
                  <div />
                </div>

                {visibleRows.length ===
                0 ? (
                  <div
                    className="px-5 py-12 text-center text-sm"
                    style={{
                      color:
                        theme.brown,
                    }}
                  >
                    No distribution
                    centers match these
                    filters.
                  </div>
                ) : (
                  visibleRows.map(
                    (row) => (
                      <button
                        key={`${row.distributor}-${row.dc}`}
                        type="button"
                        onClick={() =>
                          openDc(row)
                        }
                        className="group grid w-full grid-cols-[1.4fr_0.75fr_0.75fr_0.7fr_0.8fr_0.75fr_1.45fr_34px] items-center gap-4 border-b px-5 py-4 text-left transition hover:bg-[#FCFAF6]"
                        style={{
                          borderColor:
                            theme.softLine,
                        }}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <div
                              className="text-[16px] font-semibold"
                              style={{
                                color:
                                  theme.charcoal,
                              }}
                            >
                              {row.dc}
                            </div>

                            <DistributorBadge
                              distributor={
                                row.distributor
                              }
                            />
                          </div>

                          <div
                            className="mt-1.5 flex items-center gap-1.5 text-xs font-medium"
                            style={{
                              color: theme.brown,
                            }}
                          >
                            <Clock3 className="h-3.5 w-3.5" />

                            {row.planning_lead_time_days != null
                              ? `${formatNumber(
                                  row.planning_lead_time_days
                                )}-day lead time`
                              : "Lead time unavailable"}

                            <span
                              style={{
                                color: "#B8ADA2",
                              }}
                            >
                              ·
                            </span>

                            {row.sku_count}{" "}
                            {row.sku_count === 1
                              ? "SKU"
                              : "SKUs"}
                          </div>

                          <div
                            className="mt-1 text-[11px] font-medium"
                            style={{
                              color: "#9B8E81",
                            }}
                          >
                            Inventory reported{" "}
                            {formatReportDate(row.report_date)}
                          </div>
                        </div>

                        <div>
                          <div
                            className="text-[16px] font-semibold"
                            style={{
                              color:
                                theme.charcoal,
                            }}
                          >
                            {formatNumber(
                              row.quantity_on_hand_cases
                            )}
                          </div>

                          <div
                            className="mt-0.5 text-[11px]"
                            style={{
                              color:
                                theme.brown,
                            }}
                          >
                            cases
                          </div>
                        </div>

                        <div>
                          <div
                            className="text-[16px] font-semibold"
                            style={{
                              color:
                                theme.charcoal,
                            }}
                          >
                            {formatNumber(
                              row.quantity_on_po_cases
                            )}
                          </div>

                          <div
                            className="mt-0.5 text-[11px]"
                            style={{
                              color:
                                theme.brown,
                            }}
                          >
                            cases
                          </div>
                        </div>

                        <div>
                          <div
                            className="text-[16px] font-semibold"
                            style={{
                              color:
                                theme.charcoal,
                            }}
                          >
                            {row.weeks_on_hand !=
                            null
                              ? formatNumber(
                                  row.weeks_on_hand,
                                  1
                                )
                              : "—"}
                          </div>

                          <div
                            className="mt-0.5 text-[11px]"
                            style={{
                              color:
                                theme.brown,
                            }}
                          >
                            weeks
                          </div>
                        </div>

                        <div>
                          <div
                            className="text-[16px] font-semibold"
                            style={{
                              color:
                                theme.charcoal,
                            }}
                          >
                            {formatNumber(
                              row.velocity_cases_per_week,
                              1
                            )}
                          </div>

                          <div
                            className="mt-0.5 text-[11px]"
                            style={{
                              color:
                                theme.brown,
                            }}
                          >
                            cs / week
                          </div>
                        </div>

                        <div>
                          <div
                            className="text-[16px] font-semibold"
                            style={{
                              color:
                                theme.charcoal,
                            }}
                          >
                            {formatNumber(
                              row.oos_events_l6m
                            )}
                          </div>

                          <div
                            className="mt-0.5 text-[11px]"
                            style={{
                              color:
                                theme.brown,
                            }}
                          >
                            {row.oos_history_complete
                              ? "events"
                              : "current only"}
                          </div>
                        </div>

                        <InventoryStateBar
                          row={row}
                        />

                        <ChevronRight
                          className="h-5 w-5 transition-transform group-hover:translate-x-0.5"
                          style={{
                            color:
                              "#AA9E92",
                          }}
                        />
                      </button>
                    )
                  )
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
