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

/*
TYPE DEFINITIONS
These tell TypeScript what our API returns
*/
type MetricRow = {
  month_year: string
  value: number
}

/*
Dummy pie chart data (you'll replace later)
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
Fake pie data for now
*/
const pieData1: PieRow[] = [
  { name: "A", value: 400 },
  { name: "B", value: 300 },
  { name: "C", value: 200 },
]

const pieData2: PieRow[] = [
  { name: "X", value: 500 },
  { name: "Y", value: 250 },
  { name: "Z", value: 150 },
]


const pieColors1 = ["#3b82f6", "#93c5fd", "#dbeafe"]
const pieColors2 = ["#10b981", "#6ee7b7", "#d1fae5"]




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
  filters: {
    chain: string[]
    channel: string[]
    year: string[]
  }
) {
  const params = new URLSearchParams()

  filters.chain.forEach((value) => params.append("chain", value))
  filters.channel.forEach((value) => params.append("channel", value))
  filters.year.forEach((value) => params.append("year", value))

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
    <Card className="rounded-2xl border-0 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle style={{ color: BAR_COLOR }} className="text-sm">
          {title}
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="text-2xl font-bold text-slate-900">
          {value}
        </div>
      </CardContent>
    </Card>
  )
}



/*
Reusable bar chart component
*/
function BarChartCard({
  title,
  data,
}: {
  title: string
  data: MetricRow[]
}) {
  return (
    <Card className="rounded-2xl border-0 shadow-sm">

      <CardHeader>
        <CardTitle style={{ color: BAR_COLOR }}>
          {title}
        </CardTitle>
      </CardHeader>

      <CardContent>

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
                <ChartTooltipContent
                  formatter={(value) => formatNumber(value)}
                />
              }
            />

            <Bar
              dataKey="value"
              fill={BAR_COLOR}
              radius={[6, 6, 0, 0]}

              label={{
                position: "top",
                fill: BAR_COLOR,
                fontWeight: 700,
                formatter: formatNumber,
              }}
            />

          </BarChart>

        </ChartContainer>

      </CardContent>

    </Card>
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
  chartTitle,
  data,
  kpi1Title,
  kpi1Value,
  kpi2Title,
  kpi2Value,
}: {
  chartTitle: string
  data: MetricRow[]
  kpi1Title: string
  kpi1Value: string
  kpi2Title: string
  kpi2Value: string
}) {

  return (

    <div className="space-y-6">

      <div className="grid grid-cols-2 gap-4">

        <KpiCard
          title={kpi1Title}
          value={kpi1Value}
        />

        <KpiCard
          title={kpi2Title}
          value={kpi2Value}
        />

      </div>

      <BarChartCard
        title={chartTitle}
        data={data}
      />

    </div>
  )
}



/*
MAIN PAGE COMPONENT
*/
export default function Home() {

  /*
  FILTER STATE
  */
  const [filters, setFilters] = useState({
    chain: [] as string[],
    channel: [] as string[],
    year: [] as string[],
  })

  const [chainOptions, setChainOptions] = useState<string[]>([])
  const [channelOptions, setChannelOptions] = useState<string[]>([])
  const [yearOptions, setYearOptions] = useState<string[]>([])

  const [activeFilter, setActiveFilter] = useState<"chain" | "channel" | "year" | null>(null)

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
      year: [],
    })
  }

  /*
  DATA STATES
  */
  const [unitsData, setUnitsData] = useState<MetricRow[]>([])
  const [buyersData, setBuyersData] = useState<MetricRow[]>([])
  const [velocityData, setVelocityData] = useState<MetricRow[]>([])
  const [podsData, setPodsData] = useState<MetricRow[]>([])



  useEffect(() => {
    async function loadChains() {
      const res = await fetch("http://127.0.0.1:8000/filters/chains")
      const data = await res.json()
      setChainOptions(data)
    }

    async function loadChannels() {
      const res = await fetch("http://127.0.0.1:8000/filters/channels")
      const data = await res.json()
      setChannelOptions(data)
    }

    async function loadYears() {
      const res = await fetch ("http://127.0.0.1:8000/filters/years")
      const data = await res.json()
      setYearOptions(data)
    }


  loadChains()
  loadChannels()
  loadYears()
}, [])

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

  const filterConfigs = [
    {
      key: "chain",
      label: "Retailer",
      options: chainOptions,
      accent: theme.blue,
    },
    {
      key: "channel",
      label: "Channel",
      options: channelOptions,
      accent: theme.gold,
    },
    {
      key: "year",
      label: "Period",
      options: yearOptions,
      accent: theme.blue,
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
    label: "Period",
    value: filters.year.length ? filters.year.join(", ") : "All Time",
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

      const urls = [
        buildMetricUrl("units", filters),
        buildMetricUrl("buyers", filters),
        buildMetricUrl("velocity", filters),
        buildMetricUrl("pods", filters),
      ]

      /* console.log(urls) */

      const responses = await Promise.all(urls.map(url => fetch(url)))

      const data = await Promise.all(responses.map(res => res.json()))

      setUnitsData(data[0])
      setBuyersData(data[1])
      setVelocityData(data[2])
      setPodsData(data[3])
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

          <div className="flex items-center gap-4">

            <Image
              src="/logo.png"
              alt="Logo"
              width={120}
              height={40}
            />

            <h1 className="text-2xl font-bold">
              CPG Dashboard
            </h1>

          </div>


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
                      item.key === "channel" ? theme.gold : theme.blue

                    return (
                      <div key={item.key} className="flex items-center gap-3">
                        <button
                          className="group relative w-[220px] truncate pb-1 text-left align-top transition"                          style={{ color: theme.charcoal }}
                          onClick={() =>
                            setActiveFilter((prev) =>
                              prev === item.key ? null : (item.key as "chain" | "channel" | "year")
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
          {activeConfig.options.map((item) => {
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
            chartTitle="Units"
            data={unitsData}
            kpi1Title="Total Units"
            kpi1Value={formatNumber(unitsStats.total)}
            kpi2Title="Latest Month"
            kpi2Value={formatNumber(unitsStats.latest)}
          />

          <ChartSection
            chartTitle="Buyers"
            data={buyersData}
            kpi1Title="Total Buyers"
            kpi1Value={formatNumber(buyersStats.total)}
            kpi2Title="Peak Month"
            kpi2Value={formatNumber(buyersStats.max)}
          />

          <ChartSection
            chartTitle="Velocity"
            data={velocityData}
            kpi1Title="Avg Velocity"
            kpi1Value={formatNumber(velocityStats.avg)}
            kpi2Title="Latest Velocity"
            kpi2Value={formatNumber(velocityStats.latest)}
          />

          <ChartSection
            chartTitle="PODs"
            data={podsData}
            kpi1Title="Total PODs"
            kpi1Value={formatNumber(podsStats.total)}
            kpi2Title="Peak PODs"
            kpi2Value={formatNumber(podsStats.max)}
          />

        </div>

      </div>

    </main>

  )
}