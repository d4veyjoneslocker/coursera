"use client"

/*
This page is a CLIENT COMPONENT because we are:
- using useState
- using useEffect
- fetching data from the API
*/

import { useEffect, useState } from "react"
import Image from "next/image"

/*
These are UI components from shadcn
They are just styled layout pieces
*/
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

/*
ChartContainer + ChartTooltip come from shadcn's chart helpers
They wrap the Recharts charts
*/
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"

/*
These are the actual chart primitives from Recharts
*/
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

/*
Filter UI components
*/

import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { useMemo} from "react"

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

const SKU_COLORS: Record<string, string> = {
  "VANILLA BEAN": "#92B9DC",
  "PEANUT BUTTER": "#F7B045",
  "MOCHA JOE": "#705C4F",
  "STRAWBERRY": "#F8AAB9",
}

const FILTER_KEYS = [
  "chain",
  "state",
  "channel",
  "sku",
  "distributor",
  "dc",
  "year",
  "month",
]

type FilterState = {
  chain: string[]
  channel: string[]
  sku: string[]
  distributor: string[]
  dc: string[]
  state: string[]
  year: string[]
  month: string[]
}

/*
TYPE DEFINITIONS
These tell TypeScript what our API returns
*/
type MetricRow = {
  month_year: string
  value: number
}

/*
Establishing pie chart form
*/
type PieRow = {
  name: string
  value: number
}


/*
Color used for bars and KPI headers
*/
const BAR_COLOR = "#3b82f6"


/*
Config object used by ChartContainer
*/
const chartConfig = {
  value: {
    label: "Value",
    color: BAR_COLOR,
  },
}




/*
Formats "2025-03" into "Mar 2025"
*/
function formatMonth(month: string) {
  const [year, monthNum] = month.split("-")
  const date = new Date(Number(year), Number(monthNum) - 1)

  return date.toLocaleString("en-US", {
    month: "short",
    year: "numeric",
  })
}



/*
Formats numbers into dashboard style
11448 -> 11.4K
*/
function formatNumber(value: unknown) {
  const num = Number(value)

  if (Number.isNaN(num)) return ""

  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M"
  if (num >= 1000) return (num / 1000).toFixed(1) + "K"
  if (num < 5) return num.toFixed(1)

  return num.toString()
}



/*
Builds the API URL including filters

Example result:
http://127.0.0.1:8000/units?chain=WholeFoods
*/

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


/*
Reusable KPI card component
Used above each chart
*/
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



/*
Reusable bar chart component
*/
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
        <BarChart data={data}>
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
          />
          <ChartTooltip
            content={
              <ChartTooltipContent formatter={(value) => formatNumber(value)} />
            }
          />
          <Bar
            dataKey="value"
            fill={accentColor}
            radius={[6, 6, 0, 0]}
            label={{
              position: "top",
              formatter: formatNumber,
              fontSize: 11,
              fontWeight: 800,
              fill: accentColor,
            }}
          />
        </BarChart>
      </ChartContainer>
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

  return (
    <div className="w-full h-full">
      <ChartContainer config={chartConfig} className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <ChartTooltip
              content={
                <ChartTooltipContent formatter={(value) => formatNumber(value)} />
              }
            />

            <Pie
              data={safeData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={52}
              outerRadius={95}
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
              x="50%"
              y="46%"
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#7A746B"
              fontSize={11}
              fontWeight={500}
              letterSpacing="0.16em"
            >
              TOTAL
            </text>

            <text
              x="50%"
              y="55%"
              textAnchor="middle"
              dominantBaseline="middle"
              fill={theme.charcoal}
              fontSize={22}
              fontWeight={600}
            >
              {formatNumber(total)}
            </text>
          </PieChart>
        </ResponsiveContainer>
      </ChartContainer>
    </div>
  )
}

/*
Calculates metrics used in the KPI cards
*/
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



/*
Reusable chart section

Structure:

KPI KPI
CHART
*/
function ChartSection({
  sectionLabel,
  chartTitle,
  data,
  kpi1Title,
  kpi1Value,
  kpi2Title,
  kpi2Value,
  accentColor,
}: {
  sectionLabel: string
  chartTitle: string
  data: MetricRow[]
  kpi1Title: string
  kpi1Value: string
  kpi2Title: string
  kpi2Value: string
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
            style={{ backgroundColor: accentColor + "CC"}}
          />

          <p
            className="text-[16px] uppercase tracking-[0.18em] font-medium"
            style={{ color: "#6B6B6B" }}
          >
            {sectionLabel}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <KpiCard title={kpi1Title} value={kpi1Value} />
          <KpiCard title={kpi2Title} value={kpi2Value} />
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



/*
MAIN PAGE COMPONENT
*/
export default function Home() {

  /*
  FILTER STATE
  */
  const [filters, setFilters] = useState<FilterState>({
    chain: [] as string[],
    channel: [] as string[],
    sku: [] as string[],
    distributor: [] as string[],
    dc: [] as string[],
    state: [] as string[],
    year: [] as string[],
    month: [] as string[],
  })

  const [filterOptions, setFilterOptions] = useState<FilterState>({
    chain: [],
    channel: [],
    sku: [],
    distributor: [],
    dc: [],
    state: [],
    year: [],
    month: [],
  })

const [activeFilter, setActiveFilter] = useState<keyof typeof filters | null>(null)

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
      year: [],
      month: [],
    })
  }

  /*
  DATA STATES
  */
  const [unitsData, setUnitsData] = useState<MetricRow[]>([])
  const [buyersData, setBuyersData] = useState<MetricRow[]>([])
  const [velocityData, setVelocityData] = useState<MetricRow[]>([])
  const [podsData, setPodsData] = useState<MetricRow[]>([])
  const [skuPieData, setSkuPieData] = useState<PieRow[]>([])


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
      key: "year",
      label: "Period",
      options: filterOptions.year,
      accent: theme.brown,
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
    key: "year",
    label: "Year",
    value: filters.year.length ? filters.year.join(", ") : "All Time",
  },
  {
    key: "sku",
    label: "SKU",
    value: filters.sku.length ? filters.sku.join(", ") : "All SKUs",
  },
  ] as const

  const activeConfig = filterConfigs.find((f) => f.key === activeFilter) ?? null

  /*
  FETCH DATA

  This runs:
  - when page loads
  - when the filter changes
  */
  useEffect(() => {

    async function loadData() {
      const filterKeys = Object.keys(filters)
      const queryString = buildMetricUrl("temp", filters).split("?")[1] ?? ""

      const filterOptionUrls = filterKeys.map(
        (key) => `http://127.0.0.1:8000/filters/${key}${queryString ? `?${queryString}` : ""}`
      )

      const metricUrls = [
        buildMetricUrl("units", filters),
        buildMetricUrl("buyers", filters),
        buildMetricUrl("velocity", filters),
        buildMetricUrl("pods", filters),
        buildMetricUrl("skus", filters)
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
      year: Array.isArray(filterOptionData[filterKeys.indexOf("year")])
        ? (filterOptionData[filterKeys.indexOf("year")] as string[])
        : [],
      month: Array.isArray(filterOptionData[filterKeys.indexOf("month")])
        ? (filterOptionData[filterKeys.indexOf("month")] as string[])
        : [],
    }

      console.log("filterKeys", filterKeys)
      console.log("filterOptionData", filterOptionData)
      console.log("nextFilterOptions", nextFilterOptions)

      setFilterOptions(nextFilterOptions)

      setUnitsData(metricData[0])
      setBuyersData(metricData[1])
      setVelocityData(metricData[2])
      setPodsData(metricData[3])
      setSkuPieData(metricData[4] as PieRow[])
    }

    loadData()

  }, [filters])



  /*
  KPI CALCULATIONS
  */
  const unitsStats = getMetricStats(unitsData)
  const buyersStats = getMetricStats(buyersData)
  const velocityStats = getMetricStats(velocityData)
  const podsStats = getMetricStats(podsData)



  return (

    <main   className="min-h-screen p-8"
            style={{ backgroundColor: theme.bg }}>

      <div className="mx-auto max-w-7xl space-y-8">


        {/* HEADER */}

        <div className="flex items-center justify-between">


          {/* FILTER */}

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
                          : item.key === "year"
                          ? theme.brown
                          : item.key === "chain"
                          ? theme.blue
                          : theme.blue

                    return (
                      <div key={item.key} className="flex items-center gap-3">
                        <button
                          className="group relative w-[220px] truncate pb-1 text-left align-top transition"                          style={{ color: theme.charcoal }}
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



        {/* DASHBOARD GRID */}

        <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">

          <ChartSection
            sectionLabel="Sales"
            chartTitle="Units"
            data={unitsData}
            kpi1Title="Total Units"
            kpi1Value={formatNumber(unitsStats.total)}
            kpi2Title="Latest Month"
            kpi2Value={formatNumber(unitsStats.latest)}
            accentColor={theme.blue}
          />

          <ChartSection
            sectionLabel = "Distribution"
            chartTitle="Buyers"
            data={buyersData}
            kpi1Title="Total Buyers"
            kpi1Value={formatNumber(buyersStats.total)}
            kpi2Title="Peak Month"
            kpi2Value={formatNumber(buyersStats.max)}
            accentColor={theme.gold}
          />

          <ChartSection
            sectionLabel = "Velocity"
            chartTitle="VPO"
            data={velocityData}
            kpi1Title="Avg Velocity"
            kpi1Value={formatNumber(velocityStats.avg)}
            kpi2Title="Latest Velocity"
            kpi2Value={formatNumber(velocityStats.latest)}
            accentColor={theme.brown}
          />

          <ChartSection
            sectionLabel = "Points of Distribution"
            chartTitle="PODs"
            data={podsData}
            kpi1Title="Total PODs"
            kpi1Value={formatNumber(podsStats.total)}
            kpi2Title="Peak PODs"
            kpi2Value={formatNumber(podsStats.max)}
            accentColor={theme.charcoal}
          />
        </div>
        <div className="grid grid-cols-1 gap-10 xl:grid-cols-3">
        <Card
          className="rounded-[28px] shadow-sm"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <CardContent className="pt-2 pb-4 px-6 space-y-6">

            {/* Header line (same style as others) */}
            <div className="flex items-center gap-3">
              <div
                className="h-[3px] w-24 rounded-full"
                style={{ backgroundColor: theme.charcoal + "CC" }}
              />
              <p
                className="text-[16px] uppercase tracking-[0.18em] font-medium"
                style={{ color: "#6B6B6B" }}
              >
                SKU MIX
              </p>
            </div>

            {/* Chart container */}
            <div
              className="rounded-[24px] border p-4"
              style={{
                backgroundColor: "#FCFAF6",
                borderColor: "#EEE5D8",
              }}
            >
              <div className="h-[300px]">
                <PieChartCard
                  data={skuPieData}
                  colorMap={SKU_COLORS}
                />
              </div>
            </div>

          </CardContent>
        </Card><Card
          className="rounded-[28px] shadow-sm"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <CardContent className="pt-2 pb-4 px-6 space-y-6">

            {/* Header line (same style as others) */}
            <div className="flex items-center gap-3">
              <div
                className="h-[3px] w-24 rounded-full"
                style={{ backgroundColor: theme.charcoal + "CC" }}
              />
              <p
                className="text-[16px] uppercase tracking-[0.18em] font-medium"
                style={{ color: "#6B6B6B" }}
              >
                SKU MIX
              </p>
            </div>

            {/* Chart container */}
            <div
              className="rounded-[24px] border p-4"
              style={{
                backgroundColor: "#FCFAF6",
                borderColor: "#EEE5D8",
              }}
            >
              <div className="h-[300px]">
                <PieChartCard
                  data={skuPieData}
                  colorMap={SKU_COLORS}
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