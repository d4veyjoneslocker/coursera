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
  Legend
} from "recharts"

/*
Table components
:/


/*
Filter UI components
*/

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import FilterBar, { FilterKey } from "@/components/ui/FilterBar"
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

const SKU_COLORS: Record<string, string> = {
  "VANILLA BEAN": "#92B9DC",
  "PEANUT BUTTER": "#F7B045",
  "MOCHA JOE": "#705C4F",
  "STRAWBERRY": "#F8AAB9",
}

const CHANNEL_COLORS: Record<string, string> = {
  "SUPERMARKET": "#6B8FD6",
  "E-COMMERCE": "#5FA8A0",
  "NATURAL": "#9A7FBF",
  "INDEPENDENT": "#D8B98A",
  "ALTERNATIVE": "#D97C6C",
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

function formatWholeNumber(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPercent(value: number) {
  const pct = Math.abs(value * 100)

  if (pct >= 1000) {
    const short = pct / 1000
    return short >= 10 ? `${Math.round(short)}K` : `${short.toFixed(1)}K`
  }

  return Math.round(pct).toString()
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
  sideLabel,
  sideValue,
}: {
  title: string
  value: string
  sideLabel?: string
  sideValue?: number
}) {
  const isPositive = sideValue !== undefined && sideValue > 0
  const isNegative = sideValue !== undefined && sideValue < 0

  const chipStyles =
    isPositive
      ? {
          bg: "#EEF6F0",
          border: "#D7E8DB",
          text: "#5F7F68",
          arrowBg: "#E4F0E7",
        }
      : isNegative
      ? {
          bg: "#FBF0F0",
          border: "#EEDADA",
          text: "#A06161",
          arrowBg: "#F6E6E6",
        }
      : {
          bg: "#F4F1EC",
          border: "#E7DED2",
          text: "#7A746B",
          arrowBg: "#ECE6DD",
        }

  return (
    <div
      className="rounded-[22px] border px-4 pt-5 pb-4"
      style={{
        backgroundColor: "#FCFAF6",
        borderColor: "#EEE5D8",
      }}
    >
      {/* Top row: title + pill */}
      <div className="flex items-start justify-between gap-3">
        <p
          className="text-xs uppercase tracking-[0.12em]"
          style={{ color: theme.brown }}
        >
          {title}
        </p>

        {sideValue !== undefined ? (
          <div className="flex flex-col items-end gap-1">
            <div
              className="inline-flex items-center gap-1.5 rounded-full border px-2 py-1"
              style={{
                backgroundColor: chipStyles.bg,
                borderColor: chipStyles.border,
                color: chipStyles.text,
              }}
            >
              <span
                className="flex items-center justify-center rounded-full"
                style={{ backgroundColor: chipStyles.arrowBg }}
              >
                {isPositive ? (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path
                      d="M2 8L8 2M8 2H3.8M8 2V6.2"
                      stroke="currentColor"
                      strokeWidth="1.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : isNegative ? (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path
                      d="M2 2L8 8M8 8H3.8M8 8V3.8"
                      stroke="currentColor"
                      strokeWidth="1.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path
                      d="M2 5H8"
                      stroke="currentColor"
                      strokeWidth="1.2"
                      strokeLinecap="round"
                    />
                  </svg>
                )}
              </span>

              <span className="text-[12px] font-semibold leading-none">
                {formatPercent(sideValue)}%
              </span>
            </div>

            {sideLabel && (
              <span
                className="text-[10px] uppercase tracking-[0.12em]"
                style={{ color: theme.brown, opacity: 0.72 }}
              >
                {sideLabel}
              </span>
            )}
          </div>
        ) : (
          <div className="w-[92px]" />
        )}
      </div>

      {/* Value row */}
      <div
        className="mt-3 text-[28px] font-semibold leading-none tracking-[-0.01em]"
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
  const isTwoColumn = safeData.length > 10

  return (
    <div
      className="grid w-fit gap-x-8 gap-y-2 text-[12px]"
      style={{
        gridTemplateColumns: isTwoColumn ? "repeat(2, max-content)" : "max-content",
      }}
    >
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
                        {Math.round(Number(data.value) * 100)}%
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
  kpis,
  accentColor,
}: {
  sectionLabel: string
  chartTitle: string
  data: MetricRow[]
  kpis: {
    key: string
    title: string
    value: number
    sideValue?: number | null
    sideLabel?: string | null
  }[]
  accentColor: string
}) {
  console.log("kpis", kpis)
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

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {Array.isArray(kpis) && kpis.map((kpi) => (
            <KpiCard
              key={kpi.key}
              title={kpi.title}
              value={formatNumber(kpi.value)}
              sideValue={kpi.sideValue ?? undefined}
              sideLabel={kpi.sideLabel ?? undefined}
            />
          ))}
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

    const [visibleFilters, setVisibleFilters] = useState<FilterKey[]>([
    "chain",
    "channel",
    "sku",
    "distributor",
    "year"
  ])



  /*
  DATA STATES
  */
  const [unitsData, setUnitsData] = useState<MetricRow[]>([])
  const [buyersData, setBuyersData] = useState<MetricRow[]>([])
  const [velocityData, setVelocityData] = useState<MetricRow[]>([])
  const [podsData, setPodsData] = useState<MetricRow[]>([])
  const [skuPieData, setSkuPieData] = useState<PieRow[]>([])
  const [channelPieData, setChannelPieData] = useState<PieRow[]>([])
  const [chainTableData, setChainTableData] = useState<any[]>([])
  const [unitsKpis, setUnitsKpis] = useState<any[]>([])
  const [buyersKpis, setBuyersKpis] = useState<any[]>([])
  const [velocityKpis, setVelocityKpis] = useState<any[]>([])
  const [podKpis, setPodKpis] = useState<any[]>([])


  
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
        buildMetricUrl("skus", filters),
        buildMetricUrl("channels", filters),
        buildMetricUrl("chain_table", filters)
      ]

      const responses = await Promise.all(
        [...filterOptionUrls, ...metricUrls].map((url) => fetch(url))
      )

      const data = await Promise.all(responses.map((res) => res.json()))

      const filterOptionData = data.slice(0, filterKeys.length)
      const metricData = data.slice(filterKeys.length)
      const chainTableDataRaw = metricData[6]

      const kpiRes = await fetch(`http://127.0.0.1:8000/kpis${queryString ? `?${queryString}` : ""}`)
      const kpiData = await kpiRes.json()

      console.log("KPI URL:", kpiRes)

      setUnitsKpis(kpiData.units_kpis ?? [])
      setBuyersKpis(kpiData.buyers_kpis ?? [])
      setVelocityKpis(kpiData.velocity_kpis ?? [])
      setPodKpis(kpiData.pod_kpis ?? [])

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
      setChannelPieData(metricData[5] as PieRow[])
      setChainTableData(chainTableDataRaw)
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
        <DashboardHeader
          brandName="Smearcase"
          subtitle="National Retail Sales"
          logoSrc="/smearcase_vanilla.png"
          lastUpdated="Mar 2026"
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
            "year",
            "month",
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
            year: "Year",
            month: "Month",
          }}
        />




        {/* DASHBOARD GRID */}

        <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">

          <ChartSection
            sectionLabel="Sales"
            chartTitle="Units"
            data={unitsData}
            kpis={unitsKpis}
            accentColor={theme.blue}
          />

          <ChartSection
            sectionLabel="Distribution"
            chartTitle="Buyers"
            data={buyersData}
            kpis={buyersKpis}
            accentColor={theme.gold}
          />

          <ChartSection
            sectionLabel="Velocity"
            chartTitle="VPO"
            data={velocityData}
            kpis={velocityKpis}
            accentColor={theme.brown}
          />

          <ChartSection
            sectionLabel="Points of Distribution"
            chartTitle="PODs"
            data={podsData}
            kpis={podKpis}
            accentColor={theme.charcoal}
          />
        </div>

        <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">

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
              <div className="h-[240px] flex items-center">
                <PieChartCard
                  data={skuPieData}
                  colorMap={SKU_COLORS}
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
          <CardContent className="pt-2 pb-4 px-6 space-y-6">

            {/* Header line (same style as others) */}
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

            {/* Chart container */}
            <div
              className="rounded-[24px] border p-4"
              style={{
                backgroundColor: "#FCFAF6",
                borderColor: "#EEE5D8",
              }}
            >
              <div className="h-[240px] flex items-center">
                <PieChartCard
                  data={channelPieData}
                  colorMap={CHANNEL_COLORS}
                />
              </div>
            </div>

          </CardContent>
        </Card>


        </div>
        <div className="mt-6 rounded-[28px] border border-black/10 bg-white/95 p-6 shadow-[0_8px_30px_rgba(0,0,0,0.06)]">
          <div className="mb-4 flex items-center gap-3">
            <div
              className="h-[3px] w-24 rounded-full"
              style={{ backgroundColor: theme.blue + "CC" }}
            />
            <p
              className="text-[16px] uppercase tracking-[0.18em] font-medium"
              style={{ color: "#6B6B6B" }}
            >
              CHAIN PERFORMANCE
            </p>
          </div>

            <div className="overflow-hidden rounded-[20px] border border-black/10">
              <div className="max-h-[420px] overflow-auto">
                <Table>
                  <TableHeader   
                    className="sticky top-0 z-10 [&_th]:text-white [&_th]:text-[12px] [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-[0.14em]"
                    style={{ backgroundColor: theme.blue }}>
                    <TableRow className="border-b border-black/10">
                      <TableHead className="h-12 px-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">
                        Chain
                      </TableHead>
                      <TableHead className="h-12 px-4 text-right text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">
                        Revenue
                      </TableHead>
                      <TableHead className="h-12 px-4 text-right text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">
                        Units
                      </TableHead>
                      <TableHead className="h-12 px-4 text-right text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">
                        Buying Stores
                      </TableHead>
                      <TableHead className="h-12 px-4 text-right text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">
                        1M Growth
                      </TableHead>
                      <TableHead className="h-12 px-4 text-right text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">
                        3M Growth
                      </TableHead>
                    </TableRow>
                  </TableHeader>

                  <TableBody>
                    {chainTableData.length > 0 ? (
                      chainTableData.map((row, index) => (
                        <TableRow
                          key={index}
                          className="border-b border-black/5 transition-colors hover:bg-neutral-50"
                        >
                          <TableCell className="px-4 py-3 text-sm font-medium text-neutral-900">
                            {row.chain ?? "—"}
                          </TableCell>

                          <TableCell className="px-4 py-3 text-right text-sm tabular-nums text-neutral-700">
                            {row.revenue != null
                              ? `$${Number(row.revenue).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                              : "—"}
                          </TableCell>

                          <TableCell className="px-4 py-3 text-right text-sm tabular-nums text-neutral-700">
                            {row.units != null
                              ? Number(row.units).toLocaleString()
                              : "—"}
                          </TableCell>

                          <TableCell className="px-4 py-3 text-right text-sm tabular-nums text-neutral-700">
                            {row.buying_stores != null
                              ? Number(row.buying_stores).toLocaleString()
                              : "—"}
                          </TableCell>

                          <TableCell className="px-4 py-3 text-right text-sm tabular-nums text-neutral-700">
                            {row.units_l1m_pct != null ? (
                              <div className="inline-flex items-center justify-end gap-1">
                                <span
                                  className="text-xs"
                                  style={{
                                    color:
                                      Number(row.units_l1m_pct) > 0
                                        ? "#16A34A"
                                        : Number(row.units_l1m_pct) < 0
                                        ? "#DC2626"
                                        : "#737373",
                                  }}
                                >
                                  {Number(row.units_l1m_pct) > 0
                                    ? "↑"
                                    : Number(row.units_l1m_pct) < 0
                                    ? "↓"
                                    : "•"}
                                </span>

                                <span
                                  style={{
                                    color:
                                      Number(row.units_l1m_pct) > 0
                                        ? "#16A34A"
                                        : Number(row.units_l1m_pct) < 0
                                        ? "#DC2626"
                                        : "#737373",
                                  }}
                                >
                                  {Math.round(Number(row.units_l1m_pct) * 100)}%
                                </span>
                              </div>
                            ) : (
                              "—"
                            )}
                          </TableCell>

                          <TableCell className="px-4 py-3 text-right text-sm tabular-nums text-neutral-700">
                            {row.units_l3m_pct != null ? (
                              <div className="inline-flex items-center justify-end gap-1">
                                <span
                                  className="text-xs"
                                  style={{
                                    color:
                                      Number(row.units_l3m_pct) > 0
                                        ? "#16A34A"
                                        : Number(row.units_l3m_pct) < 0
                                        ? "#DC2626"
                                        : "#737373",
                                  }}
                                >
                                  {Number(row.units_l3m_pct) > 0
                                    ? "↑"
                                    : Number(row.units_l3m_pct) < 0
                                    ? "↓"
                                    : "•"}
                                </span>

                                <span
                                  style={{
                                    color:
                                      Number(row.units_l3m_pct) > 0
                                        ? "#16A34A"
                                        : Number(row.units_l3m_pct) < 0
                                        ? "#DC2626"
                                        : "#737373",
                                  }}
                                >
                                  {Math.round(Number(row.units_l3m_pct) * 100)}%
                                </span>
                              </div>
                            ) : (
                              "—"
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell
                          colSpan={6}
                          className="px-4 py-10 text-center text-sm text-neutral-500"
                        >
                          No data matches the selected filters.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        


      </div>

    </main>

  )
}