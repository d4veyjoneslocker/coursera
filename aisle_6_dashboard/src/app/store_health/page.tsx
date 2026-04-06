"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { Card, CardContent } from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts"

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

type FilterState = {
  chain: string[]
  channel: string[]
  sku: string[]
  distributor: string[]
  dc: string[]
  state: string[]
}

type MetricRow = {
  month_year: string
  value: number
}

type PieRow = {
  name: string
  value: number
}

const BAR_COLOR = "#3b82f6"

const chartConfig = {
  value: {
    label: "Value",
    color: BAR_COLOR,
  },
}

function formatMonth(month: string) {
  const [year, monthNum] = month.split("-")
  const date = new Date(Number(year), Number(monthNum) - 1)

  return date.toLocaleString("en-US", {
    month: "short",
    year: "numeric",
  })
}

function formatNumber(value: unknown) {
  const num = Number(value)

  if (Number.isNaN(num)) return ""
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M"
  if (num >= 1000) return (num / 1000).toFixed(1) + "K"
  if (num < 5) return num.toFixed(1)

  return num.toString()
}

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
    ? `http://127.0.0.1:8000/${endpoint}?${query}`
    : `http://127.0.0.1:8000/${endpoint}`
}

function KpiCard({
  title,
  value,
}: {
  title: string
  value: string
}) {
  return (
    <div
      className="rounded-[22px] border p-4"
      style={{
        backgroundColor: "#FCFAF6",
        borderColor: "#EEE5D8",
      }}
    >
      <p
        className="text-xs uppercase tracking-[0.12em]"
        style={{ color: theme.brown }}
      >
        {title}
      </p>

      <div
        className="mt-2 text-3xl font-semibold"
        style={{ color: theme.charcoal }}
      >
        {value}
      </div>
    </div>
  )
}

function BarChartCard({
  data,
  accentColor,
}: {
  data: MetricRow[]
  accentColor: string
}) {
  return (
    <div className="w-full">
      <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
        <BarChart data={data} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" />
          <XAxis
            dataKey="month_year"
            tickFormatter={formatMonth}
            tickLine={false}
            axisLine={false}
            tickMargin={10}
          />
          <YAxis
            tickFormatter={formatNumber}
            tickLine={false}
            axisLine={false}
            tickMargin={10}
            width={50}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(label) => {
                  const date = new Date(label)
                  return date.toLocaleString("en-US", {
                    month: "long",
                    year: "numeric",
                  })
                }}
              />
            }
          />
          <Bar
            dataKey="value"
            fill={accentColor}
            radius={[6, 6, 0, 0]}
            label={{
              position: "top",
              formatter: formatNumber,
              fontSize: 16,
              fontWeight: 600,
              fill: accentColor,
            }}
          />
        </BarChart>
      </ChartContainer>
    </div>
  )
}

function PieLegend({
  data,
  colorMap,
}: {
  data: PieRow[]
  colorMap: Record<string, string>
}) {
  const safeData = Array.isArray(data) ? data : []

  return (
    <div className="grid w-fit gap-x-8 gap-y-2 text-[12px]">
      {safeData.map((item) => (
        <div key={item.name} className="flex items-center gap-2">
          <div
            className="h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: colorMap[item.name] || "#D1D5DB" }}
          />
          <span style={{ color: "#6B6B6B" }}>{item.name}</span>
        </div>
      ))}
    </div>
  )
}

function PieChartCard({
  data,
  colorMap,
}: {
  data: PieRow[]
  colorMap: Record<string, string>
}) {

  const safeData = Array.isArray(data) ? data : []
  const total = safeData.reduce((sum, row) => sum + row.value, 0)

  const pieCx = "51%"
  const pieCy = "50%"


  return (
    <div className="grid w-full grid-cols-[2fr_1fr] items-center gap-x-0">
      <div className="flex h-[220px] w-full items-center justify-center">
        <div className="h-[220px] w-[220px]">
          <ChartContainer config={chartConfig} className="h-full w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <ChartTooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null

                    const data = payload[0].payload

                    return (
                      <div
                        className="rounded-[12px] border px-3 py-2 shadow-sm"
                        style={{
                          backgroundColor: "#FFFEFB",
                          borderColor: "#E5DDD0",
                        }}
                      >
                        <div
                          className="text-sm font-semibold"
                          style={{ color: theme.charcoal }}
                        >
                          {data.name}
                        </div>

                        <div
                            className="mt-1 text-sm"
                            style={{ color: "#7A746B" }}
                            >
                            {Math.round((Number(data.value) / total) * 100)}%
                            </div>
                      </div>

                    )
                  }}
                />

                <Pie
                  data={safeData}
                  dataKey="value"
                  nameKey="name"
                  cx={pieCx}
                  cy={pieCy}
                  innerRadius={52}
                  outerRadius={85}
                  paddingAngle={2}
                  stroke="none"
                >
                  {safeData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={colorMap[entry.name] || "#D1D5DB"}
                    />
                  ))}
                </Pie>

                <text
                  x={pieCx}
                  y={pieCy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#7A746B"
                  fontSize={11}
                  fontWeight={500}
                  letterSpacing="0.16em"
                  dy={-10}
                >
                  TOTAL
                </text>

                <text
                  x={pieCx}
                  y={pieCy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={theme.charcoal}
                  fontSize={22}
                  fontWeight={600}
                  dy={12}
                >
                  {formatNumber(total)}
                </text>
              </PieChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>
      </div>

      <div className="flex h-full items-center justify-start">
        <PieLegend data={safeData} colorMap={colorMap} />
      </div>
    </div>
  )
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

function ChartSection({
  sectionLabel,
  data,
  kpi1Title,
  kpi1Value,
  kpi2Title,
  kpi2Value,
  kpi3Title,
  kpi3Value,
  accentColor,
}: {
  sectionLabel: string
  data: MetricRow[]
  kpi1Title: string
  kpi1Value: string
  kpi2Title: string
  kpi2Value: string
  kpi3Title: string
  kpi3Value: string
  accentColor: string
}) {
  return (
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
            style={{ backgroundColor: accentColor + "CC" }}
          />

          <p
            className="text-[16px] uppercase tracking-[0.18em] font-medium"
            style={{ color: "#6B6B6B" }}
          >
            {sectionLabel}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <KpiCard title={kpi1Title} value={kpi1Value} />
          <KpiCard title={kpi2Title} value={kpi2Value} />
          <KpiCard title={kpi3Title} value={kpi3Value} />
        </div>

        <div
          className="rounded-[24px] border p-4"
          style={{
            backgroundColor: "#FCFAF6",
            borderColor: "#EEE5D8",
          }}
        >
          <BarChartCard data={data} accentColor={accentColor} />
        </div>
      </CardContent>
    </Card>
  )
}

export default function StoresPage() {
  const [filters, setFilters] = useState<FilterState>({
    chain: [],
    channel: [],
    sku: [],
    distributor: [],
    dc: [],
    state: [],
  })

  const [filterOptions, setFilterOptions] = useState<FilterState>({
    chain: [],
    channel: [],
    sku: [],
    distributor: [],
    dc: [],
    state: [],
  })

  const [activeFilter, setActiveFilter] =
    useState<keyof typeof filters | null>(null)

  const [barOneData, setBarOneData] = useState<MetricRow[]>([])
  const [barTwoData, setBarTwoData] = useState<MetricRow[]>([])
  const [pieData, setPieData] = useState<PieRow[]>([])

  function toggleFilterValue(filterKey: keyof typeof filters, value: string) {
    setFilters((prev) => {
      const currentValues = prev[filterKey]
      const alreadySelected = currentValues.includes(value)

      return {
        ...prev,
        [filterKey]: alreadySelected
          ? currentValues.filter((v) => v !== value)
          : [...currentValues, value],
      }
    })
  }

  function clearFilter(filterKey: keyof typeof filters) {
    setFilters((prev) => ({
      ...prev,
      [filterKey]: [],
    }))
  }

  function clearAllFilters() {
    setFilters({
      chain: [],
      channel: [],
      sku: [],
      distributor: [],
      dc: [],
      state: [],
    })
  }

  const filterConfigs = [
    {
      key: "chain",
      label: "Retailer",
      options: filterOptions.chain,
      accent: theme.blue,
    },
    {
      key: "channel",
      label: "Channel",
      options: filterOptions.channel,
      accent: theme.gold,
    },
    {
      key: "sku",
      label: "SKU",
      options: filterOptions.sku,
      accent: theme.charcoal,
    },
  ] as const

  const contextItems = [
    {
      key: "chain",
      label: "Retailer",
      value: filters.chain.length ? filters.chain.join(", ") : "All Retailers",
    },
    {
      key: "channel",
      label: "Channel",
      value: filters.channel.length ? filters.channel.join(", ") : "All Channels",
    },
    {
      key: "sku",
      label: "SKU",
      value: filters.sku.length ? filters.sku.join(", ") : "All SKUs",
    },
  ] as const

  const activeConfig = filterConfigs.find((f) => f.key === activeFilter) ?? null

  useEffect(() => {
    async function loadData() {
      const filterKeys = Object.keys(filters)
      const queryString = buildMetricUrl("temp", filters).split("?")[1] ?? ""

      const filterOptionUrls = filterKeys.map(
        (key) =>
          `http://127.0.0.1:8000/filters/${key}${queryString ? `?${queryString}` : ""}`
      )

      const metricUrls = [
        buildMetricUrl("buyers", filters),
        buildMetricUrl("velocity", filters),
        buildMetricUrl("reorder_stats", filters),
      ]

      const responses = await Promise.all(
        [...filterOptionUrls, ...metricUrls].map((url) => fetch(url))
      )

      const data = await Promise.all(responses.map((res) => res.json()))

      const filterOptionData = data.slice(0, filterKeys.length)
      const metricData = data.slice(filterKeys.length)

      const nextFilterOptions: FilterState = {
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
    }

    loadData()
  }, [filters])

  const barOneStats = getMetricStats(barOneData)
  const barTwoStats = getMetricStats(barTwoData)

  return (
    <main className="min-h-screen p-8" style={{ backgroundColor: theme.bg }}>
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="rounded-full border px-4 py-2 text-sm font-medium transition"
              style={{
                borderColor: "#D8CFBF",
                color: theme.brown,
                backgroundColor: "#FAF7F1",
              }}
            >
              Dashboard
            </Link>

            <Link
              href="/stores"
              className="rounded-full border px-4 py-2 text-sm font-medium transition"
              style={{
                borderColor: theme.line,
                color: theme.charcoal,
                backgroundColor: theme.surface,
              }}
            >
              Stores
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-6 w-full">
          <div
            className="relative rounded-[28px] border px-6 py-6 shadow-[0_10px_30px_rgba(52,51,50,0.05)]"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.line,
            }}
          >
            <div className="flex items-start gap-6">
              <div className="space-y-3">
                <p
                  className="text-xs uppercase tracking-[0.2em]"
                  style={{ color: theme.brown }}
                >
                  Viewing
                </p>

                <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[28px] font-medium tracking-tight">
                  {contextItems.map((item, i) => {
                    const accent =
                      item.key === "channel"
                        ? theme.gold
                        : item.key === "sku"
                        ? theme.charcoal
                        : theme.blue

                    return (
                      <div key={item.key} className="flex items-center gap-3">
                        <button
                          className="group relative w-[220px] truncate pb-1 text-left align-top transition"
                          style={{ color: theme.charcoal }}
                          onClick={() =>
                            setActiveFilter((prev) =>
                              prev === item.key ? null : item.key
                            )
                          }
                          title={item.value}
                        >
                          {item.value}
                          <span
                            className="absolute inset-x-0 bottom-0 h-[2px] rounded-full opacity-80"
                            style={{ backgroundColor: accent }}
                          />
                        </button>

                        {i < contextItems.length - 1 && (
                          <span className="text-xl" style={{ color: "#B8AB97" }}>
                            •
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  <button
                    className="rounded-full border px-3 py-1.5 text-xs font-medium"
                    style={{
                      borderColor: "#D8CFBF",
                      color: theme.brown,
                      backgroundColor: "#FAF7F1",
                    }}
                    onClick={() => setActiveFilter("chain")}
                  >
                    Change filters
                  </button>

                  <button
                    className="rounded-full px-3 py-1.5 text-xs font-medium"
                    style={{ color: theme.brown }}
                    onClick={clearAllFilters}
                  >
                    Reset view
                  </button>
                </div>
              </div>
            </div>

            {activeConfig && (
              <div
                className={`absolute left-6 top-[calc(100%+12px)] z-30 w-[360px] rounded-[28px] border p-5 shadow-[0_18px_40px_rgba(52,51,50,0.12)] transition-all duration-200 ease-out origin-top-left ${
                  activeConfig
                    ? "translate-y-0 scale-100 opacity-100"
                    : "pointer-events-none -translate-y-1 scale-[0.98] opacity-0"
                }`}
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.line,
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p
                      className="text-xs uppercase tracking-[0.18em]"
                      style={{ color: theme.brown }}
                    >
                      Change {activeConfig.label.toLowerCase()}
                    </p>
                    <h2
                      className="mt-1 text-xl font-semibold"
                      style={{ color: theme.charcoal }}
                    >
                      {activeConfig.label} selector
                    </h2>
                  </div>

                  <button
                    className="rounded-full px-2.5 py-1 text-xs font-medium"
                    style={{
                      backgroundColor: theme.chip,
                      color: theme.charcoal,
                    }}
                    onClick={() => setActiveFilter(null)}
                  >
                    close
                  </button>
                </div>

                <input
                  readOnly
                  placeholder={`Search ${activeConfig.label.toLowerCase()}...`}
                  className="mt-4 w-full rounded-xl border px-3 py-2.5 text-sm outline-none"
                  style={{
                    borderColor: "#DDD4C6",
                    backgroundColor: "#FFFEFB",
                    color: theme.charcoal,
                  }}
                />

                <div className="mt-4 max-h-[320px] space-y-2 overflow-y-auto pr-1">
                  {(Array.isArray(activeConfig.options) ? activeConfig.options : []).map((item) => {
                    const isSelected = filters[activeConfig.key].includes(item)

                    return (
                      <button
                        key={item}
                        className="flex w-full items-center justify-between rounded-2xl border px-3 py-3 text-left text-sm transition"
                        style={{
                          borderColor: isSelected ? "#CFE0EE" : "#EEE6DA",
                          backgroundColor: isSelected ? theme.chip : "#FFFEFB",
                          color: theme.charcoal,
                        }}
                        onClick={() => toggleFilterValue(activeConfig.key, item)}
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <div
                            className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold"
                            style={{
                              borderColor: isSelected ? activeConfig.accent : "#CFC3B1",
                              backgroundColor: isSelected ? activeConfig.accent : "transparent",
                              color: isSelected ? "white" : "transparent",
                            }}
                          >
                            ✓
                          </div>

                          <span className="truncate">{item}</span>
                        </div>

                        {isSelected && (
                          <span
                            className="ml-3 shrink-0 text-xs font-medium"
                            style={{ color: theme.brown }}
                          >
                            selected
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>

                <div className="mt-4 flex gap-3">
                  <button
                    className="text-sm font-medium"
                    style={{ color: activeConfig.accent }}
                    onClick={() => clearFilter(activeConfig.key)}
                  >
                    Clear
                  </button>

                  <button
                    className="text-sm font-medium"
                    style={{ color: theme.brown }}
                    onClick={() => setActiveFilter(null)}
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">
          <ChartSection
            sectionLabel="Store Metric One"
            data={barOneData}
            kpi1Title="Total"
            kpi1Value={formatNumber(barOneStats.total)}
            kpi2Title="Latest"
            kpi2Value={formatNumber(barOneStats.latest)}
            kpi3Title="Peak"
            kpi3Value={formatNumber(barOneStats.max)}
            accentColor={theme.blue}
          />

          <ChartSection
            sectionLabel="Store Metric Two"
            data={barTwoData}
            kpi1Title="Total"
            kpi1Value={formatNumber(barTwoStats.total)}
            kpi2Title="Latest"
            kpi2Value={formatNumber(barTwoStats.latest)}
            kpi3Title="Peak"
            kpi3Value={formatNumber(barTwoStats.max)}
            accentColor={theme.gold}
          />
        </div>

        <div className="grid grid-cols-1 gap-10">
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
                  STORE MIX
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
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  )
}