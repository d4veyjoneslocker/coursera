"use client"

import Link from "next/link"
import { useEffect, useMemo, useRef, useState } from "react"
import { useOrg } from "@/components/OrgContext"

import { Card, CardContent } from "@/components/ui/card"

import ChartSection from "@/components/ui/charts/ChartSection"
import { PieChartCard } from "@/components/ui/charts/ChartCards"
import type { MetricRow, PieRow } from "@/components/ui/charts/chartTypes"
import FilterBar from "@/components/ui/filters/FilterBar"
import DashboardHeader from "@/components/ui/DashboardHeader"
import { InsightsSection } from "@/components/InsightsSection"
import { formatWhole, formatPercent } from "@/lib/format"

const DEFAULT_THEME = {
  primary_color: "#9A93B0",
  secondary_color: "#C58E82",
  accent_color: "#C8795A",
  charcoal: "#343332",
  cream: "#E9E2C8",
  bg: "#F6F2EA",
  line: "#E5DDD0",
  chip: "#EEF4F8",
  surface: "#FFFDF9",
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

const DATA_ENDPOINTS = {
  statusPie: "store_health/status",
  channels: "store_health/channels",
  storeTable: "store_health/store_performance",
  kpis: "store_health/kpis",
  filters: "store_health/filters",
} as const

const STATUS_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  Healthy: {
    bg: "#EEF6F0",
    text: "#5F7F68",
    border: "#D7E8DB",
  },
  Struggling: {
    bg: "#FFF4E8",
    text: "#A56A2A",
    border: "#EFD9BC",
  },
  Inactive: {
    bg: "#F4F1EC",
    text: "#7A746B",
    border: "#E7DED2",
  },
  New: {
    bg: "#EEF4F8",
    text: "#4E6F8C",
    border: "#D5E1EA",
  },
  Revived: {
    bg: "#F3EEFF",
    text: "#6B4FB3",
    border: "#DDD3F5",
  },
}

type OrgLike = {
  name?: string | null
  logo_url?: string | null
  primary_color?: string | null
  secondary_color?: string | null
  accent_color?: string | null
  background_color?: string | null
  last_refreshed_at?: string | null
}

function formatLastUpdated(value?: string | null) {
  if (!value) return "—"

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"

  return date.toLocaleString("en-US", {
    month: "long",
    year: "numeric",
  })
}

function buildQueryString(filters: Record<string, string[]>) {
  const params = new URLSearchParams()

  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => params.append(key, value))
  })

  return params.toString()
}

function buildApiUrl(
  endpoint: string,
  filters: Record<string, string[]>,
  orgId: string
) {
  const params = new URLSearchParams()

  // 🔥 ALWAYS include org_id
  params.set("org_id", orgId)

  // add filters
  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => params.append(key, value))
  })

  return `${API_BASE_URL}/${endpoint}?${params.toString()}`
}

function buildFilterUrl(
  columnName: string,
  filters: Record<string, string[]>,
  orgId: string
) {
  const params = new URLSearchParams()

  params.set("column_name", columnName)

  // 🔥 ALWAYS include org_id
  params.set("org_id", orgId)

  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => params.append(key, value))
  })

  return `${API_BASE_URL}/store_health/filters?${params.toString()}`
}

function StatusPill({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.Inactive

  return (
    <span
      className="inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium"
      style={{
        backgroundColor: style.bg,
        color: style.text,
        borderColor: style.border,
      }}
    >
      {status}
    </span>
  )
}

function SortableHeader({
  label,
  column,
  sortKey,
  sortDirection,
  onSort,
}: {
  label: string
  column: string
  sortKey: string | null
  sortDirection: "asc" | "desc"
  onSort: (key: string) => void
}) {
  const isActive = sortKey === column

  return (
    <th
      onClick={() => onSort(column)}
      className="group cursor-pointer px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-white"
    >
      <div className="flex items-center gap-1">
        <span>{label}</span>
        <span
          className={`text-[10px] transition-opacity ${
            isActive ? "opacity-100" : "opacity-0 group-hover:opacity-60"
          }`}
        >
          {isActive ? (sortDirection === "asc" ? "↑" : "↓") : "↕"}
        </span>
      </div>
    </th>
  )
}

export default function StoresPage() {
  const {org, skuColors} = useOrg()

  const theme = useMemo(() => {
    return {
      ...DEFAULT_THEME,
      primary_color: org?.primary_color || DEFAULT_THEME.primary_color,
      secondary_color: org?.secondary_color || DEFAULT_THEME.secondary_color,
      accent_color: org?.accent_color || DEFAULT_THEME.accent_color,
      bg: org?.background_color || DEFAULT_THEME.bg,
    }
  }, [org])

  const PIE_COLORS: Record<string, string> = {
    Healthy: theme.primary_color,
    Struggling: theme.secondary_color,
    Inactive: theme.accent_color,
    Revived: theme.charcoal,
    New: theme.cream,
  }

  const FILTER_KEYS = [
    "chain",
    "channel",
    "distributor",
    "dc",
    "state",
    "status",
  ] as const

  const [filters, setFilters] = useState<Record<string, string[]>>({
    chain: [],
    channel: [],
    distributor: [],
    dc: [],
    state: [],
    status: [],
  })

  const [filterOptions, setFilterOptions] = useState<Record<string, string[]>>({
    chain: [],
    channel: [],
    distributor: [],
    dc: [],
    state: [],
    status: [],
  })

  const [visibleFilters, setVisibleFilters] = useState<string[]>([
    "chain",
    "channel",
    "distributor",
    "status",
  ])

  const latestRequestRef = useRef(0)

  const [pieData, setPieData] = useState<PieRow[]>([])
  const [channelMix, setChannelMix] = useState<PieRow[]>([])
  const [storeTableData, setStoreTableData] = useState<any[]>([])
  const [channelPieKpis, setChannelPieKpis] = useState<{
    key: string
    title: string
    value: number
  } | null>(null)
  const [statusCenterValue, setStatusCenterValue] = useState<number | string | undefined>(undefined)

  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc")

  const processedStoreTableData = [...storeTableData]
    .filter((row) => {
      const selectedStatuses = filters.status ?? []
      return selectedStatuses.length === 0 ? true : selectedStatuses.includes(row.status)
    })
    .sort((a, b) => {
      if (!sortKey) return 0

      const aVal = a[sortKey]
      const bVal = b[sortKey]

      if (aVal == null) return 1
      if (bVal == null) return -1

      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDirection === "asc" ? aVal - bVal : bVal - aVal
      }

      return sortDirection === "asc"
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal))
    })

  function handleSort(key: string) {
    if (sortKey !== key) {
      setSortKey(key)
      setSortDirection("desc")
    } else if (sortDirection === "desc") {
      setSortDirection("asc")
    } else {
      setSortKey(null)
    }
  }

  async function loadData() {
      if (!org?.id) return

      const requestId = ++latestRequestRef.current

      try {
        const filterRequests = Object.fromEntries(
          FILTER_KEYS.map((key) => [key, buildFilterUrl(key, filters, org.id)])
        )

        const dataRequests = {
          statusPie: buildApiUrl(DATA_ENDPOINTS.statusPie, filters, org.id),
          channels: buildApiUrl(DATA_ENDPOINTS.channels, filters, org.id),
          storeTable: buildApiUrl(DATA_ENDPOINTS.storeTable, filters, org.id),
          kpis: buildApiUrl(DATA_ENDPOINTS.kpis, filters, org.id),
        }

        const requestMap = {
          ...filterRequests,
          ...dataRequests,
        }

        const responseEntries = await Promise.all(
          Object.entries(requestMap).map(async ([key, url]) => {
            const response = await fetch(url)
            const json = await response.json()
            return [key, json] as const
          })
        )

        const results = Object.fromEntries(responseEntries)

        if (requestId !== latestRequestRef.current) {
          console.log("IGNORED STALE STORE HEALTH RESPONSE", { requestId })
          return
        }

        setFilterOptions({
          chain: Array.isArray(results.chain) ? results.chain : [],
          channel: Array.isArray(results.channel) ? results.channel : [],
          distributor: Array.isArray(results.distributor) ? results.distributor : [],
          dc: Array.isArray(results.dc) ? results.dc : [],
          state: Array.isArray(results.state) ? results.state : [],
          status: Array.isArray(results.status) ? results.status : [],
        })

        setPieData(
          results.statusPie && !Array.isArray(results.statusPie)
            ? Object.entries(results.statusPie).map(([name, value]) => ({
                name,
                value: Number(value),
              }))
            : []
        )

        setChannelMix(Array.isArray(results.channels) ? results.channels : [])
        setStoreTableData(Array.isArray(results.storeTable) ? results.storeTable : [])

        const kpiData = results.kpis ?? {}

        setChannelPieKpis(kpiData.count_channel?.channel_count ?? null)

        const totalBuyersKpi = Array.isArray(kpiData.buying_kpis)
          ? kpiData.buying_kpis.find((item: any) => item?.key === "total_buyers")
          : null

        setStatusCenterValue(totalBuyersKpi?.value)
      } catch (error) {
        console.error("Failed to load store health page data:", error)
      }
    }

  useEffect(() => {
    loadData()
  }, [filters, org?.id])

  const [dataThrough, setDataThrough] = useState<string | undefined>()
  const [isStale, setIsStale] = useState(false)

  const formatMonthYear = (value?: string) => {
    if (!value) return undefined

    const [year, month] = value.split("-")
    const date = new Date(Number(year), Number(month) - 1)

    return date.toLocaleString("en-US", {
      month: "long",
      year: "numeric",
    })
  }

  const fetchStatus = async () => {
    if (!org?.id) return

    try {
      const res = await fetch(
        `${API_BASE_URL}/distributors/kehe/status?org_id=${org.id}`
      )
      const data = await res.json()

      if (data.status === "ready") {
        setDataThrough(formatMonthYear(data.data_through))
        setIsStale(data.is_stale)
      }
    } catch (err) {
      console.error("Failed to fetch status", err)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [org.id])

  const CHANNEL_COLORS = [
  "#6B8FD6", // blue
  "#5FA8A0", // teal
  "#9A7FBF", // purple
  "#D8B98A", // tan
  "#D97C6C", // muted red
  "#8FA58E", // green
]
  

  const channelColors = Object.fromEntries(
    (channelMix ?? []).map((row, index) => [
      row.name,
      CHANNEL_COLORS[index % CHANNEL_COLORS.length],
    ])
  )

  return (
    <main
      className="min-h-screen"
      style={{ backgroundColor: theme.bg }}
    >
      <DashboardHeader
        activePage="stores"
        dataThrough={dataThrough}
        isStale={isStale}
        onDataRefresh={async () => {
          await fetchStatus()
          await loadData()
        }}
      />

      <div className="ml-[238px] min-h-screen p-8">
        <div className="mx-auto max-w-7xl space-y-8">

          <FilterBar
          filters={filters}
          setFilters={setFilters}
          filterOptions={filterOptions}
          availableFilters={[
            "chain",
            "channel",
            "distributor",
            "dc",
            "state",
            "status",
          ]}
          visibleFilters={visibleFilters}
          setVisibleFilters={setVisibleFilters}
          filterLabels={{
            chain: "Retailer",
            channel: "Channel",
            distributor: "Distributor",
            dc: "DC",
            state: "State",
            status: "Status",
          }}
          theme = {theme}
        />

        <InsightsSection orgId={org?.id ?? null} filters={filters} endpoint="store-health"/>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Card
            className="rounded-[28px] shadow-sm"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.line,
            }}
          >
            <CardContent className="space-y-6 px-6 pt-2 pb-4">
              <div className="flex items-center gap-3">
                <div
                  className="h-[3px] w-24 rounded-full"
                  style={{ backgroundColor: theme.charcoal + "CC" }}
                />
                <p
                  className="text-[16px] font-medium uppercase tracking-[0.18em]"
                  style={{ color: "#6B6B6B" }}
                >
                  STORE HEALTH
                </p>
              </div>

              <div
                className="rounded-[24px] border p-4"
                style={{
                  backgroundColor: "#FCFAF6",
                  borderColor: "#EEE5D8",
                }}
              >
                <div className="flex h-[240px] items-center">
                  <PieChartCard
                    data={pieData}
                    colorMap={PIE_COLORS}
                    centerLabel="TOTAL STORES"
                    theme={theme}
                    tooltipValueType="number"
                    centerValue={Number(statusCenterValue)}
                    centerValueFormatter={formatWhole}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card
            className="rounded-[28px] shadow-sm"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.line,
            }}
          >
            <CardContent className="space-y-6 px-6 pt-2 pb-4">
              <div className="flex items-center gap-3">
                <div
                  className="h-[3px] w-24 rounded-full"
                  style={{ backgroundColor: theme.primary_color + "CC" }}
                />
                <p
                  className="text-[16px] font-medium uppercase tracking-[0.18em]"
                  style={{ color: "#6B6B6B" }}
                >
                  CHANNEL MIX
                </p>
              </div>

              <div
                className="rounded-[24px] border p-4"
                style={{
                  backgroundColor: "#FCFAF6",
                  borderColor: "#EEE5D8",
                }}
              >
                <div className="flex h-[240px] items-center">
                  <PieChartCard
                    data={channelMix}
                    colorMap={channelColors}
                    centerValue={channelPieKpis?.value}
                    centerLabel={channelPieKpis?.title}
                    theme={theme}
                    tooltipValueType="percent"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div
          className="rounded-[28px] border p-6 shadow-sm"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <div className="mb-4 flex items-center gap-3">
            <div
              className="h-[3px] w-24 rounded-full"
              style={{ backgroundColor: theme.accent_color + "CC" }}
            />
            <p
              className="text-[16px] font-medium uppercase tracking-[0.18em]"
              style={{ color: "#6B6B6B" }}
            >
              STORE STATUS DETAIL
            </p>
          </div>

          <div className="mb-4 flex flex-wrap gap-2">
            {["All", "Healthy", "Struggling", "Inactive", "Revived", "New"].map((status) => {
              const selectedStatuses = filters.status ?? []
              const isActive =
                status === "All"
                  ? selectedStatuses.length === 0
                  : selectedStatuses.includes(status)
              const style = status === "All" ? null : STATUS_STYLES[status]

              return (
                <button
                  key={status}
                  className="rounded-full border px-3 py-1.5 text-xs font-medium transition"
                  style={
                    status === "All"
                      ? {
                          borderColor: isActive ? theme.charcoal : "#D8CFBF",
                          backgroundColor: isActive ? theme.charcoal : "#FAF7F1",
                          color: isActive ? "#FFFFFF" : theme.accent_color,
                        }
                      : {
                          borderColor: isActive ? style!.border : "#D8CFBF",
                          backgroundColor: isActive ? style!.bg : "#FAF7F1",
                          color: isActive ? style!.text : theme.accent_color,
                        }
                  }
                  onClick={() =>
                    setFilters((prev) => ({
                      ...prev,
                      status: status === "All" ? [] : [status],
                    }))
                  }
                >
                  {status}
                </button>
              )
            })}
          </div>

          <div className="overflow-hidden rounded-[20px] border border-black/10">
            <div className="max-h-[420px] overflow-auto">
              <table className="w-full text-sm">
                <thead
                  className="sticky top-0 z-10"
                  style={{ backgroundColor: theme.primary_color }}
                >
                  <tr className="[&_th]:px-4 [&_th]:py-3 [&_th]:text-left [&_th]:text-[11px] [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-[0.14em] [&_th]:text-white">
                    <th onClick={() => handleSort("coded_customer")} className="cursor-pointer">
                      Store
                    </th>

                    <SortableHeader
                      label="Units"
                      column="units"
                      sortKey={sortKey}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="Revenue"
                      column="revenue"
                      sortKey={sortKey}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="Reorders"
                      column="reorders"
                      sortKey={sortKey}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="VPO"
                      column="vpo"
                      sortKey={sortKey}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="First Month"
                      column="first_month_purchased"
                      sortKey={sortKey}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="Last Month"
                      column="last_month_purchased"
                      sortKey={sortKey}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="Status"
                      column="status"
                      sortKey={sortKey}
                      sortDirection={sortDirection}
                      onSort={handleSort}
                    />
                  </tr>
                </thead>

                <tbody>
                  {processedStoreTableData.length > 0 ? (
                    processedStoreTableData.map((row, index) => (
                      <tr
                        key={`${row.coded_customer}-${index}`}
                        className="border-b border-black/5"
                      >
                        <td className="px-4 py-3 font-medium text-neutral-900">
                          {row.coded_customer ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-neutral-700">
                          {row.units != null ? Number(row.units).toLocaleString() : "—"}
                        </td>
                        <td className="px-4 py-3 text-neutral-700">
                          {row.revenue != null
                            ? `$${Number(row.revenue).toLocaleString(undefined, {
                                maximumFractionDigits: 0,
                              })}`
                            : "—"}
                        </td>
                        <td className="px-4 py-3 text-neutral-700">
                          {row.reorders != null ? Number(row.reorders).toLocaleString() : "—"}
                        </td>
                        <td className="px-4 py-3 text-neutral-700">
                          {row.vpo != null ? Number(row.vpo).toFixed(1) : "—"}
                        </td>
                        <td className="px-4 py-3 text-neutral-700">
                          {row.first_month_purchased ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-neutral-700">
                          {row.last_month_purchased ?? "—"}
                        </td>
                        <td className="px-4 py-3">
                          <StatusPill status={row.status ?? "Inactive"} />
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-4 py-10 text-center text-sm text-neutral-500"
                      >
                        No stores match the selected status.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>
)
}