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
  brown: string
  charcoal: string
}

export function BarChartCard({
  data,
  accentColor,
  valueFormatter = formatNumber,   // 👈 add this
}: {
  data: MetricRow[]
  accentColor: string
  valueFormatter?: (value: number) => string
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
                  fill={theme.brown}
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