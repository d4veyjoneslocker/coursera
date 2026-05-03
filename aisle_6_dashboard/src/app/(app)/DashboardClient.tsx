"use client"

import { useOrg } from "@/components/OrgContext"
import { useEffect, useMemo, useRef, useState } from "react"

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

import CustomLegend from "@/components/ui/CustomLegend"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import FilterBar from "@/components/ui/filters/FilterBar"
import DashboardHeader from "@/components/ui/DashboardHeader"
import KpiCard from "@/components/ui/charts/KpiCard"
import { InsightsSection } from "@/components/InsightsSection"
import ChartSection from "@/components/ui/charts/ChartSection"


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

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





const FILTER_KEYS = [
  "chain",
  "state",
  "channel",
  "sku",
  "distributor",
  "dc",
  "year",
  "month_year",
] as const

const DATA_ENDPOINTS = {
  units: "overview/units",
  buyers: "overview/buyers",
  velocity: "overview/velocity",
  pods: "overview/pods",
  skuMix: "overview/skus",
  channelMix: "overview/channels",
  chainTable: "overview/chain_table",
  kpis: "overview/kpis",
} as const

type MetricRow = {
  month_year: string
  value: number
}

type PieRow = {
  name: string
  value: number
}

type KpiItem = {
  key: string
  title: string
  value: number
  sideValue?: number | null
  sideLabel?: string | null
  sideType?: "percent" | "absolute" | null
}

type OrgLike = {
  id: string
  name: string
  primary_color: string | null
  secondary_color: string | null
  accent_color: string | null
  background_color: string | null
  logo_url: string | null
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

function formatPercent(value: number) {
  const pct = Math.abs(value * 100)

  if (pct >= 1000) {
    const short = pct / 1000
    return short >= 10 ? `${Math.round(short)}K` : `${short.toFixed(1)}K`
  }

  return Math.round(pct).toString()
}

function formatNumber(value: unknown) {
  const num = Number(value)

  if (Number.isNaN(num)) return ""

  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M"
  if (num >= 1000) return (num / 1000).toFixed(1) + "K"
  if (num >= 100) return num.toFixed(0)
  if (num < 100) return num.toFixed(1)

  return num.toString()
}

function splitCenterLabel(label: string, maxWordsPerLine = 2) {
  const words = label.toUpperCase().split(" ")

  const lines: string[] = []
  let currentLine = ""

  const MAX_CHARS_PER_LINE = 11

  words.forEach((word) => {
    if ((currentLine + " " + word).trim().length > MAX_CHARS_PER_LINE) {
      if (currentLine) lines.push(currentLine)
      currentLine = word
    } else {
      currentLine = currentLine ? `${currentLine} ${word}` : word
    }
  })

  if (currentLine) lines.push(currentLine)

  return lines
}

function buildQueryString(
  filters: Record<string, string[]>,
  orgId: string
) {
  const params = new URLSearchParams()

  params.set("org_id", orgId)

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

  const safeOrgId =
    process.env.NODE_ENV === "development"
      ? orgId || "default_org"
      : orgId

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

  const safeOrgId =
    process.env.NODE_ENV === "development"
      ? orgId || "default_org"
      : orgId

  params.set("column_name", columnName)
  params.set("org_id", orgId)

  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => params.append(key, value))
  })

  return `${API_BASE_URL}/overview/filters?${params.toString()}`
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
                labelFormatter={(label) =>
                  typeof label === "string" ? formatMonth(label) : String(label)
                }
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
              fontSize: 14,
              fontWeight: 600,
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
  centerValue,
  centerLabel,
  theme,
}: {
  data: PieRow[]
  colorMap: Record<string, string>
  centerValue?: number | string
  centerLabel?: string
  theme: typeof DEFAULT_THEME
}) {
  const safeData = Array.isArray(data) ? data : []

  const total = safeData.reduce((sum, row) => sum + row.value, 0)

  const displayValue =
    centerValue !== undefined ? centerValue : formatNumber(total)

  const centerLines = splitCenterLabel(centerLabel ?? "TOTAL")

  const pieCx = "51%"
  const pieCy = "50%"

  return (
    <div className="flex w-full justify-center">
      <div className="flex items-center gap-2">
        <div className="h-[220px] w-[220px] shrink-0">
          <ChartContainer config={chartConfig} className="h-full w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <ChartTooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null

                    const chartData = payload[0].payload

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
                          {chartData.name}
                        </div>

                        <div
                          className="mt-1 text-sm"
                          style={{ color: "#7A746B" }}
                        >
                          {Math.round(Number(chartData.value) * 100)}%
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
                  fill={theme.accent_color}
                  fontSize={11}
                  fontWeight={500}
                  letterSpacing="0.12em"
                >
                  {centerLines.map((line, index) => (
                    <tspan
                      key={index}
                      x={pieCx}
                      dy={index === 0 ? -12 : 12}
                    >
                      {line}
                    </tspan>
                  ))}
                </text>

                <text
                  x={pieCx}
                  y={pieCy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={theme.charcoal}
                  fontSize={22}
                  fontWeight={600}
                  dy={22}
                >
                  {formatNumber(displayValue)}
                </text>
              </PieChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>

        <div className="shrink-0">
          <CustomLegend data={safeData} colorMap={colorMap} />
        </div>
      </div>
    </div>
  )
}


export default function Home() {
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

  const latestRequestRef = useRef(0)


  const [filters, setFilters] = useState<Record<string, string[]>>({
    chain: [],
    channel: [],
    sku: [],
    distributor: [],
    dc: [],
    state: [],
    year: [],
    month_year: [],
  })

  const [filterOptions, setFilterOptions] = useState<Record<string, string[]>>({
    chain: [],
    channel: [],
    sku: [],
    distributor: [],
    dc: [],
    state: [],
    year: [],
    month_year: [],
  })

  const [visibleFilters, setVisibleFilters] = useState<string[]>([
    "chain",
    "channel",
    "sku",
    "distributor",
    "year",
  ])

  const [unitsData, setUnitsData] = useState<MetricRow[]>([])
  const [buyersData, setBuyersData] = useState<MetricRow[]>([])
  const [velocityData, setVelocityData] = useState<MetricRow[]>([])
  const [podsData, setPodsData] = useState<MetricRow[]>([])
  const [skuPieData, setSkuPieData] = useState<PieRow[]>([])
  const [channelPieData, setChannelPieData] = useState<PieRow[]>([])
  const [chainTableData, setChainTableData] = useState<any[]>([])
  const [unitsKpis, setUnitsKpis] = useState<KpiItem[]>([])
  const [buyersKpis, setBuyersKpis] = useState<KpiItem[]>([])
  const [velocityKpis, setVelocityKpis] = useState<KpiItem[]>([])
  const [podKpis, setPodKpis] = useState<KpiItem[]>([])
  const [skuPieKpis, setSkuPieKpis] = useState<{
    key: string
    title: string
    value: number
  } | null>(null)
  const [channelPieKpis, setChannelPieKpis] = useState<{
    key: string
    title: string
    value: number
  } | null>(null)

  const loadData = async () => {
    if (!org?.id) return

    const requestId = ++latestRequestRef.current

    console.log("LOAD DATA START", {
      requestId,
      time: new Date().toISOString(),
      filters,
    })

    try {
      const filterRequests = Object.fromEntries(
        FILTER_KEYS.map((key) => [key, buildFilterUrl(key, filters, org.id)])
      )

      const dataRequests = {
        units: buildApiUrl(DATA_ENDPOINTS.units, filters, org.id),
        buyers: buildApiUrl(DATA_ENDPOINTS.buyers, filters, org.id),
        velocity: buildApiUrl(DATA_ENDPOINTS.velocity, filters, org.id),
        pods: buildApiUrl(DATA_ENDPOINTS.pods, filters, org.id),
        skuMix: buildApiUrl(DATA_ENDPOINTS.skuMix, filters, org.id),
        channelMix: buildApiUrl(DATA_ENDPOINTS.channelMix, filters, org.id),
        chainTable: buildApiUrl(DATA_ENDPOINTS.chainTable, filters, org.id),
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
        console.log("IGNORED STALE RESPONSE", { requestId })
        return
      }

      console.log("LOAD DATA FINISH", {
        requestId,
        time: new Date().toISOString(),
        filters,
        chainTableRows: Array.isArray(results.chainTable)
          ? results.chainTable.length
          : "not array",
      })

      setFilterOptions({
        chain: Array.isArray(results.chain) ? results.chain : [],
        channel: Array.isArray(results.channel) ? results.channel : [],
        sku: Array.isArray(results.sku) ? results.sku : [],
        distributor: Array.isArray(results.distributor) ? results.distributor : [],
        dc: Array.isArray(results.dc) ? results.dc : [],
        state: Array.isArray(results.state) ? results.state : [],
        year: Array.isArray(results.year) ? results.year : [],
        month_year: Array.isArray(results.month_year) ? results.month_year : [],
      })

      setUnitsData(Array.isArray(results.units) ? results.units : [])
      setBuyersData(Array.isArray(results.buyers) ? results.buyers : [])
      setVelocityData(Array.isArray(results.velocity) ? results.velocity : [])
      setPodsData(Array.isArray(results.pods) ? results.pods : [])
      setSkuPieData(Array.isArray(results.skuMix) ? results.skuMix : [])
      setChannelPieData(Array.isArray(results.channelMix) ? results.channelMix : [])
      setChainTableData(Array.isArray(results.chainTable) ? results.chainTable : [])

      const kpiData = results.kpis ?? {}

      setUnitsKpis(kpiData.unit_kpis ?? [])
      setBuyersKpis(kpiData.buying_kpis ?? [])
      setVelocityKpis(kpiData.vpo_kpis ?? [])
      setPodKpis(kpiData.pod_kpis ?? [])
      setSkuPieKpis(kpiData.avg_skus_per_store.skus_per_store ?? null)
      setChannelPieKpis(kpiData.count_channel.channel_count ?? null)
    } catch (error) {
      console.error("Failed to load overview page data:", error)
    }
  }

  useEffect(() => {
    loadData()
  }, [filters, org?.id])

  /* The chunk below renders the date*/

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
      const res = await fetch(`${API_BASE_URL}/distributors/kehe/status?org_id=${org.id}`)
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
  }, [org?.id])

  const CHANNEL_COLORS = [
  "#6B8FD6", // blue
  "#5FA8A0", // teal
  "#9A7FBF", // purple
  "#D8B98A", // tan
  "#D97C6C", // muted red
  "#8FA58E", // green
]
  

  const channelColors = Object.fromEntries(
    (channelPieData ?? []).map((row, index) => [
      row.name,
      CHANNEL_COLORS[index % CHANNEL_COLORS.length],
    ])
  )

  return (
    <main className="min-h-screen p-8" style={{ backgroundColor: theme.bg }}>
      <div className="mx-auto max-w-7xl space-y-8">
        <DashboardHeader
          activePage="overview"
          dataThrough={dataThrough}
          isStale={isStale}
          onDataRefresh={async () => {
            await fetchStatus()
            await loadData()
          }}
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
            "month_year",
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
            month_year: "Month",
          }}
          theme = {theme}
        />

        <InsightsSection 
          orgId={org?.id ?? null} 
          filters={filters} 
          endpoint="overview"
          brandPrimary={DEFAULT_THEME.primary_color}
          brandPrimaryBg="#EAF3F9"       // soft primary_color bg (lighter version)
          brandSecondary={DEFAULT_THEME.secondary_color}
          brandSecondaryBg="#FFF4E3"     // soft gold bg
        />
        
        <div className="grid grid-cols-1 gap-10 xl:grid-cols-2">
          <ChartSection
            sectionLabel="Sales"
            data={unitsData}
            kpis={unitsKpis}
            accentColor={theme.primary_color}
            theme={theme}
            info={
              <>
                <p>Sales performance over time.</p>
                <ul className="mt-2 list-disc pl-4 text-sm text-[#705C4F]">
                  <li>Includes all distributors</li>
                  <li>Monthly aggregation</li>
                </ul>
              </>
  }
          />

          <ChartSection
            sectionLabel="Distribution"
            data={buyersData}
            kpis={buyersKpis}
            accentColor={theme.secondary_color}
            theme={theme}
          />

          <ChartSection
            sectionLabel="Velocity"
            data={velocityData}
            kpis={velocityKpis}
            accentColor={theme.accent_color}
            theme={theme}
          />

          <ChartSection
            sectionLabel="Points of Distribution"
            data={podsData}
            kpis={podKpis}
            accentColor={theme.charcoal}
            theme={theme}
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
                  SKU MIX
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
                    data={skuPieData}
                    colorMap={skuColors}
                    centerValue={skuPieKpis?.value}
                    centerLabel={skuPieKpis?.title}
                    theme={theme}
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
                    data={channelPieData}
                    colorMap={channelColors}
                    centerValue={channelPieKpis?.value}
                    centerLabel={channelPieKpis?.title}
                    theme={theme}
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
              style={{ backgroundColor: theme.primary_color + "CC" }}
            />
            <p
              className="text-[16px] font-medium uppercase tracking-[0.18em]"
              style={{ color: "#6B6B6B" }}
            >
              CHAIN PERFORMANCE
            </p>
          </div>

          <div className="overflow-hidden rounded-[20px] border border-black/10">
            <div className="max-h-[420px] overflow-auto">
              <Table>
                <TableHeader
                  className="sticky top-0 z-10 [&_th]:text-[12px] [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-[0.14em] [&_th]:text-white"
                  style={{ backgroundColor: theme.primary_color }}
                >
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
                          {row.units != null ? Number(row.units).toLocaleString() : "—"}
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