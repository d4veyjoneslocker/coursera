"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { Card, CardContent } from "@/components/ui/card"

import ChartSection from "@/components/ui/charts/ChartSection"
import { PieChartCard } from "@/components/ui/charts/ChartCards"
import { formatNumber } from "@/components/ui/charts/chartUtils"
import { formatPercent } from "@/components/ui/charts/chartUtils"
import type { MetricRow, PieRow } from "@/components/ui/charts/chartTypes"
import FilterBar from "@/components/ui/filters/FilterBar"
import DashboardHeader from "@/components/ui/DashboardHeader"

const theme = {
  blue: "#92B9DC",
  gold: "#F7B045",
  brown: "#705C4F",
  charcoal: "#343332",
  cream: "#E9E2C8",
  bg: "#F6F2EA",
  line: "#E5DDD0",
  chip: "#EEF4F8",
  surface: "#FFFDF9",
}

const PIE_COLORS: Record<string, string> = {
  Healthy: theme.blue,
  Struggling: theme.gold,
  Inactive: theme.brown,
  Revived: theme.charcoal,
  New: theme.cream,
}

const CHANNEL_COLOR_MAP: Record<string, string> = {
  "GROCERY": theme.blue,
  "E-COMMERCE": theme.gold,
  "NATURAL": theme.brown,
  "INDEPENDENT": theme.charcoal,
  "SPECIALTY": "#A8A29E",
  "ALTERNATIVE": "#D6D3D1",
}

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
    bg: "#EEF4F8",        // light blue
    text: "#4E6F8C",
    border: "#D5E1EA",
  },
  Revived: {
    bg: "#F3EEFF",        // light purple
    text: "#6B4FB3",
    border: "#DDD3F5",
  },
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL
/* const API_BASE_URL = "http://127.0.0.1:8000" */

function buildMetricUrl(
  endpoint: string,
  filters: Record<string, string[]>
) {
  const params = new URLSearchParams()

  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => params.append(key, value))
  })

  const query = params.toString()

  return query
    ? `${API_BASE_URL}/${endpoint}?${query}`
    : `${API_BASE_URL}/${endpoint}`
}



function getMetricStats(data: MetricRow[]) {
  const total = data.reduce((sum, row) => sum + row.value, 0)

  const latest = data.length
    ? data[data.length - 1].value
    : 0

  const avg = data.length
    ? Math.round(total / data.length)
    : 0

  const max = data.length
    ? Math.max(...data.map((row) => row.value))
    : 0

  return { total, latest, avg, max }
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
          {isActive
            ? sortDirection === "asc"
              ? "↑"
              : "↓"
            : "↕"}
        </span>
      </div>
    </th>
  )
}


export default function StoresPage() {
  const [filters, setFilters] = useState<Record<string, string[]>>({
    chain: [],
    channel: [],
    sku: [],
    distributor: [],
    dc: [],
    state: [],
    status: [],
  })

  const [filterOptions, setFilterOptions] = useState<Record<string, string[]>>({
    chain: [],
    channel: [],
    sku: [],
    distributor: [],
    dc: [],
    state: [],
    status: [],
  })

  const [visibleFilters, setVisibleFilters] = useState<string[]>([
  "chain",
  "channel",
  "sku",
  "distributor",
  "status",
  ])


  const [barOneData, setBarOneData] = useState<MetricRow[]>([])
  const [barTwoData, setBarTwoData] = useState<MetricRow[]>([])
  const [pieData, setPieData] = useState<PieRow[]>([])
  const [channelMix, setChannelMix] = useState<PieRow[]>([])
  const [storeTableData, setStoreTableData] = useState<any[]>([])
  const [buyersKpis, setBuyersKpis] = useState<any[]>([])
  const [reorderKpis, setReorderKpis] = useState<any[]>([])
  const [channelPieKpis, setChannelPieKpis] = useState<{
    key: string
    title: string
    value: number
  } | null>(null)

  /* States for sorting table columns */
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc")

  console.log("filters.status:", filters.status)
  console.log("storeTableData sample:", storeTableData.slice(0, 10))
  console.log(
    "unique storeTableData statuses:",
    [...new Set(storeTableData.map((row) => row.status))]
  )

  const processedStoreTableData = [...storeTableData]
    .filter((row) => {
      const selectedStatuses = filters.status ?? []
      return selectedStatuses.length === 0
        ? true
        : selectedStatuses.includes(row.status)
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
    // first click on a new column
    setSortKey(key)
    setSortDirection("desc")
  } else if (sortDirection === "desc") {
    // second click
    setSortDirection("asc")
  } else {
    // third click → reset
    setSortKey(null)
  }
  }

  

  useEffect(() => {
    async function loadData() {
      const filterKeys = Object.keys(filters)
      const queryString = buildMetricUrl("temp", filters).split("?")[1] ?? ""

      const filterOptionUrls = filterKeys.map(
        (key) =>
          `${API_BASE_URL}/filters/${key}${queryString ? `?${queryString}` : ""}`
      )

      const metricUrls = [
        buildMetricUrl("buyers", filters),
        buildMetricUrl("reorder_graph", filters),
        buildMetricUrl("reorder_stats", filters),
        buildMetricUrl("channels", filters),
        buildMetricUrl("store_level_reorder", filters),
      ]

      const responses = await Promise.all(
        [...filterOptionUrls, ...metricUrls].map((url) => fetch(url))
      )

      const data = await Promise.all(responses.map((res) => res.json()))

      const filterOptionData = data.slice(0, filterKeys.length)
      const metricData = data.slice(filterKeys.length)

      const nextFilterOptions: Record<string, string[]> = {
        chain: Array.isArray(filterOptionData[filterKeys.indexOf("chain")])
          ? (filterOptionData[filterKeys.indexOf("chain")] as string[])
          : [],
        channel: Array.isArray(filterOptionData[filterKeys.indexOf("channel")])
          ? (filterOptionData[filterKeys.indexOf("channel")] as string[])
          : [],
        sku: Array.isArray(filterOptionData[filterKeys.indexOf("sku")])
          ? (filterOptionData[filterKeys.indexOf("sku")] as string[])
          : [],
        distributor: Array.isArray(filterOptionData[filterKeys.indexOf("distributor")])
          ? (filterOptionData[filterKeys.indexOf("distributor")] as string[])
          : [],
        dc: Array.isArray(filterOptionData[filterKeys.indexOf("dc")])
          ? (filterOptionData[filterKeys.indexOf("dc")] as string[])
          : [],
        state: Array.isArray(filterOptionData[filterKeys.indexOf("state")])
          ? (filterOptionData[filterKeys.indexOf("state")] as string[])
          : [],
        status: Array.isArray(filterOptionData[filterKeys.indexOf("status")])
          ? (filterOptionData[filterKeys.indexOf("status")] as string[])
          : [],
      }

      setFilterOptions(nextFilterOptions)

      setBarOneData(metricData[0] as MetricRow[])
      setBarTwoData(metricData[1] as MetricRow[])
      setPieData(
        metricData[2] && !Array.isArray(metricData[2])
            ? Object.entries(metricData[2]).map(([name, value]) => ({
                name,
                value: Number(value),
            }))
            : []
        )
      setChannelMix(metricData[3] ?? [])
      setStoreTableData(metricData[4] as any[])

      const kpiRes = await fetch(`${API_BASE_URL}/kpis_store_health${queryString ? `?${queryString}` : ""}`)
      const kpiData = await kpiRes.json()

      console.log("queryString", queryString)
      console.log("FULL KPI DATA", kpiData)
      console.log("buyers_kpis", kpiData.buyers_kpis)
      console.log("reorder_kpis", kpiData.reorder_kpis)

      setBuyersKpis(kpiData.buyers_kpis ?? [])
      setReorderKpis(kpiData.reorder_kpis ?? [])
      setChannelPieKpis(kpiData.channel_count ?? null)
    }
    

    loadData()
  }, [filters])

  const barOneStats = getMetricStats(barOneData)
  const barTwoStats = getMetricStats(barTwoData)

  return (
    <main className="min-h-screen p-8" style={{ backgroundColor: theme.bg }}>
      <div className="mx-auto max-w-7xl space-y-8">

        <DashboardHeader
          brandName="Smearcase"
          subtitle="Store Health"
          logoSrc="/smearcase_vanilla.png"
          lastUpdated="April 2026"
          activePage="store-health"
        />

        <FilterBar
                  filters={filters}
                  setFilters={setFilters}
                  filterOptions={filterOptions}
                  availableFilters={[
                    "chain",
                    "channel",
                    "sku",
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
                    sku: "SKU",
                    distributor: "Distributor",
                    dc: "DC",
                    state: "State",
                    status: "status",
                  }}
                />

        <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">
          <ChartSection
            sectionLabel="BUYING STORES"
            data={barOneData}
            kpis={buyersKpis}
            accentColor={theme.blue}
            theme={theme}
          />

          <ChartSection
            sectionLabel="REORDER RATE"
            data={barTwoData}
            kpis={reorderKpis}
            accentColor={theme.gold}
            theme={theme}
            chartType="line"
            valueFormatter={(v) => `${formatPercent(v)}%`}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* LEFT CARD — STORE HEALTH */}
          <Card
            className="rounded-[28px] shadow-sm"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.line,
            }}
          >
            <CardContent className="pt-2 pb-4 px-6 space-y-6">
              <div className="flex items-center gap-3">
                <div
                  className="h-[3px] w-24 rounded-full"
                  style={{ backgroundColor: theme.charcoal + "CC" }}
                />
                <p
                  className="text-[16px] uppercase tracking-[0.18em] font-medium"
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
                <div className="h-[240px] flex items-center">
                  <PieChartCard
                    data={pieData}
                    colorMap={PIE_COLORS}
                    centerLabel="TOTAL STORES"
                    theme={theme}
                    tooltipValueType="number"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* RIGHT CARD — CHANNEL MIX */}
          <Card
            className="rounded-[28px] shadow-sm"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.line,
            }}
          >
            <CardContent className="pt-2 pb-4 px-6 space-y-6">
              <div className="flex items-center gap-3">
                <div
                  className="h-[3px] w-24 rounded-full"
                  style={{ backgroundColor: theme.blue + "CC" }}
                />
                <p
                  className="text-[16px] uppercase tracking-[0.18em] font-medium"
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
                <div className="h-[240px] flex items-center">
                  <PieChartCard
                    data={channelMix}
                    colorMap={CHANNEL_COLOR_MAP}
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
              style={{ backgroundColor: theme.brown + "CC" }}
            />
            <p
              className="text-[16px] uppercase tracking-[0.18em] font-medium"
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
              const style = STATUS_STYLES[status]

              return (
                <button
                  key={status}
                  className="rounded-full border px-3 py-1.5 text-xs font-medium transition"
                  style={
                    status === "All"
                      ? {
                          borderColor: isActive ? theme.charcoal : "#D8CFBF",
                          backgroundColor: isActive ? theme.charcoal : "#FAF7F1",
                          color: isActive ? "#FFFFFF" : theme.brown,
                        }
                      : {
                          borderColor: isActive ? style.border : "#D8CFBF",
                          backgroundColor: isActive ? style.bg : "#FAF7F1",
                          color: isActive ? style.text : theme.brown,
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
                  style={{ backgroundColor: theme.blue }}
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
    </main>
  )
}