"use client"

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
  Line,
  LineChart,
  LabelList,
} from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { MetricRow, PieRow } from "./chartTypes"
import {
  chartConfig,
  formatMonth,
  formatNumber,
  splitCenterLabel,
} from "./chartUtils"
import CustomLegend from "@/components/ui/CustomLegend"

type Theme = {
  surface: string
  line: string
  accent_color: string
  charcoal: string
}

function SoftLinePointLabel({
  x,
  y,
  value,
  theme,
  valueFormatter,
}: {
  x?: number
  y?: number
  value?: number | string
  theme: Theme
  valueFormatter: (value: number) => string
}) {
  if (x == null || y == null || value == null) return null

  const label = valueFormatter(Number(value))
  const width = Math.max(34, label.length * 7 + 12)

  return (
    <g>
      <rect
        x={x - width / 2}
        y={y - 28}
        width={width}
        height={20}
        rx={10}
        fill="#FFFEFB"
        stroke="#E5DDD0"
      />
      <text
        x={x}
        y={y}
        textAnchor="middle"
        dy="0.10em"
        fontSize={14}
        fontWeight={600}
        fill={theme.surface}
      >
        {label}
      </text>
    </g>
  )
}

export function BarChartCard({
  data,
  accentColor,
  valueFormatter = formatNumber,
  className = "min-h-[300px]",
}: {
  data: MetricRow[]
  accentColor: string
  valueFormatter?: (value: number) => string
  className?: string
}) {
  return (
    <div className="h-full w-full">
      <ChartContainer
        config={chartConfig}
        className={`${className} h-full w-full`}
      >
        <BarChart
          data={data}
          margin={{ top: 20, right: 20, left: -10, bottom: 0 }}
        >
          <CartesianGrid vertical={false} strokeDasharray="3 3" />

          <XAxis
            dataKey="month_year"
            tickFormatter={formatMonth}
            tickLine={false}
            axisLine={false}
            tickMargin={10}
          />

          <YAxis
            tickFormatter={valueFormatter}
            tickLine={false}
            axisLine={false}
            tickMargin={10}
            width={50}
          />

          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value) =>
                  valueFormatter(Number(value))
                }
                labelFormatter={(label) =>
                  typeof label === "string"
                    ? formatMonth(label)
                    : String(label)
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
              formatter: valueFormatter as any,
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

export function LineChartCard({
  data,
  accentColor,
  theme,
  valueFormatter = formatNumber,
  showPointLabels = true,
}: {
  data: MetricRow[]
  accentColor: string
  theme: Theme
  valueFormatter?: (value: number) => string
  showPointLabels?: boolean
}) {
  function LinePointPillLabel({
    x,
    y,
    value,
    index,
    dataLength,
    accentColor,
    valueFormatter,
  }: {
    x?: number
    y?: number
    value?: number | string
    index?: number
    dataLength: number
    accentColor: string
    valueFormatter: (value: number) => string
  }) {
    if (x == null || y == null || value == null || index == null) return null

    const isFirst = index === 0
    const isLast = index === dataLength - 1
    const isEveryOtherMiddle = index % 2 === 0

    if (!(isFirst || isLast || isEveryOtherMiddle)) return null

    const label = valueFormatter(Number(value))
    const width = Math.max(40, label.length * 8 + 16)
    const height = 22

    // 👇 KEY: anchor everything to the rect, not the point
    const rectY = y - height / 2
    const textY = rectY + height / 2 + 4

    return (
      <g>
        <rect
          x={x - width / 2}
          y={rectY}
          width={width}
          height={height}
          rx={11}
          fill={accentColor}
        />
        <text
          x={x}
          y={textY}
          textAnchor="middle"
          fontSize={14}
          fontWeight={600}
          fill={theme.surface}
        >
          {label}
        </text>
      </g>
    )
  }

  return (
    <div className="w-full">
      <ChartContainer config={chartConfig} className="min-h-[300px] w-full">
        <LineChart data={data} margin={{ top: 24, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid
            vertical={false}
            stroke={theme.line}
            strokeDasharray="3 3"
          />
          <XAxis
            dataKey="month_year"
            tickFormatter={formatMonth}
            tickLine={false}
            axisLine={false}
            tickMargin={10}
          />
          <YAxis
            tickFormatter={valueFormatter}
            tickLine={false}
            axisLine={false}
            tickMargin={10}
            width={50}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value) => valueFormatter(Number(value))}
                labelFormatter={(label) =>
                  typeof label === "string" ? formatMonth(label) : String(label)
                }
              />
            }
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={accentColor}
            strokeWidth={3}
            dot={{
              r: 4,
              fill: accentColor,
              stroke: theme.surface,
              strokeWidth: 2,
            }}
            activeDot={{
              r: 5,
              fill: theme.surface,
              stroke: accentColor,
              strokeWidth: 2,
            }}
          >
            {showPointLabels && (
              <LabelList
                dataKey="value"
                content={(props: any) => (
                  <LinePointPillLabel
                    x={props.x}
                    y={props.y}
                    value={props.value}
                    index={props.index}
                    dataLength={data.length}
                    accentColor={accentColor}
                    valueFormatter={valueFormatter}
                  />
                )}
              />
            )}
          </Line>
        </LineChart>
      </ChartContainer>
    </div>
  )
}

export function PieLegend({
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
        gridTemplateColumns: isTwoColumn
          ? "repeat(2, max-content)"
          : "max-content",
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

export function PieChartCard({
  data,
  colorMap,
  centerValue,
  centerLabel,
  theme,
  tooltipValueType = "percent",
}: {
  data: PieRow[]
  colorMap: Record<string, string>
  centerValue?: number | string
  centerLabel?: string
  theme: Theme
  tooltipValueType?: "percent" | "number"
}) {
  const safeData = Array.isArray(data) ? data : []
  const total = safeData.reduce((sum, row) => sum + row.value, 0)

  const displayValue =
    centerValue !== undefined ? centerValue : formatNumber(total)

  const centerLines = splitCenterLabel(centerLabel ?? "TOTAL")

  const pieCx = "51%"
  const pieCy = "50%"

  const formatTooltipValue = (value: number) => {
    if (tooltipValueType === "number") {
      return formatNumber(value)
    }

    return `${Math.round(value * 100)}%`
  }

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
                          {formatTooltipValue(Number(data.value))}
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

export type YoYMetricRow = {
  month: string
  month_num: number
  current_year: number
  current_value: number
  prior_year: number
  prior_value: number
}

function lightenHex(hex: string, opacity = "55") {
  return `${hex}${opacity}`
}

export function YoYBarChartCard({
  data,
  accentColor,
  valueFormatter = formatNumber,
  className = "h-full",
}: {
  data: YoYMetricRow[]
  accentColor: string
  valueFormatter?: (value: number) => string
  className?: string
}) {
  const currentYear = data?.[0]?.current_year
  const priorYear = data?.[0]?.prior_year

  return (
    <div className="h-full w-full">
      <ChartContainer
        config={chartConfig}
        className={`${className} h-full w-full`}
      >
        <BarChart
          data={data}
          margin={{ top: 24, right: 24, left: -10, bottom: 0 }}
        >
          <CartesianGrid vertical={false} strokeDasharray="3 3" />

          <XAxis
            dataKey="month"
            tickLine={false}
            axisLine={false}
            tickMargin={10}
          />

          <YAxis
            tickFormatter={valueFormatter}
            tickLine={false}
            axisLine={false}
            tickMargin={10}
            width={50}
          />

          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value, name) => {
                  const label =
                    name === "current_value"
                      ? String(currentYear)
                      : String(priorYear)

                  return [
                    valueFormatter(Number(value)),
                    label,
                  ]
                }}
              />
            }
          />

          <Bar
            dataKey="prior_value"
            name={String(priorYear)}
            fill={lightenHex(accentColor, "55")}
            radius={[6, 6, 0, 0]}
            label={{
              position: "top",
              formatter: valueFormatter as any,
              fontSize: 13,
              fontWeight: 600,
              fill: lightenHex(accentColor, "AA"),
            }}
          />

          <Bar
            dataKey="current_value"
            name={String(currentYear)}
            fill={accentColor}
            radius={[6, 6, 0, 0]}
            label={{
              position: "top",
              formatter: valueFormatter as any,
              fontSize: 13,
              fontWeight: 600,
              fill: accentColor,
            }}
          />
        </BarChart>
      </ChartContainer>
    </div>
  )
}