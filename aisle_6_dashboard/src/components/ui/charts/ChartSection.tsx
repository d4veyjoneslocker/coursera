"use client"

import { Card, CardContent } from "@/components/ui/card"
import KpiCard from "./KpiCard"
import { BarChartCard, LineChartCard } from "./ChartCards"
import type { MetricRow, KpiItem } from "./chartTypes"
import { formatNumber } from "./chartUtils"
import { ChartInfoButton } from "@/components/ui/ChartInfoButton"
import { useState } from "react"
import ExpandedChartModal from "./ExpandedChartModal"

type Theme = {
  surface: string
  line: string
  accent_color: string
  charcoal: string
}

type ChartSectionProps = {
  sectionLabel: string
  data: MetricRow[]
  kpis: KpiItem[]
  accentColor: string
  theme: Theme
  valueFormatter?: (value: number) => string
  chartType?: "bar" | "line"
  info?: React.ReactNode

  metricKey: "units" | "buyers" | "velocity" | "pods" | "reorders" | "fill_rate"
  orgId: string | null
  filters: Record<string, string[]>
}

export default function ChartSection({
  sectionLabel,
  data,
  kpis,
  accentColor,
  theme,
  valueFormatter,
  chartType = "bar",
  info,
  metricKey,
  orgId,
  filters,
}: ChartSectionProps) {
  const formatValue = (v: number) =>
    valueFormatter ? valueFormatter(v) : formatNumber(v)

  const [expandedOpen, setExpandedOpen] = useState(false)

  return (
    <>
      <Card
        onClick={() => setExpandedOpen(true)}
        className="cursor-pointer rounded-[28px] shadow-sm transition hover:shadow-md"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.line,
        }}
      >
        <CardContent className="space-y-6 px-6 pt-2 pb-4">
          {/* Header */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div
                className="h-[3px] w-24 rounded-full"
                style={{ backgroundColor: accentColor + "CC" }}
              />

              <p
                className="text-[16px] font-medium uppercase tracking-[0.18em]"
                style={{ color: "#6B6B6B" }}
              >
                {sectionLabel}
              </p>
            </div>

            {info && (
              <div onClick={(e) => e.stopPropagation()}>
                <ChartInfoButton title={sectionLabel}>
                  {info}
                </ChartInfoButton>
              </div>
            )}
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {kpis.map((kpi) => (
              <KpiCard
                key={kpi.key}
                title={kpi.title}
                value={String(formatValue(kpi.value))}
                sideValue={kpi.sideValue ?? undefined}
                sideLabel={kpi.sideLabel ?? undefined}
                sideType={kpi.sideType ?? "percent"}
                theme={theme}
              />
            ))}
          </div>

          {/* Chart */}
          <div
            className="rounded-[24px] border p-4"
            style={{
              backgroundColor: "#FCFAF6",
              borderColor: "#EEE5D8",
            }}
          >
            {chartType === "line" ? (
              <LineChartCard
                data={data}
                accentColor={accentColor}
                theme={theme}
                valueFormatter={valueFormatter}
              />
            ) : (
              <BarChartCard
                data={data}
                accentColor={accentColor}
                valueFormatter={valueFormatter}
              />
            )}
          </div>
        </CardContent>
      </Card>

      <ExpandedChartModal
        open={expandedOpen}
        onClose={() => setExpandedOpen(false)}
        sectionLabel={sectionLabel}
        data={data}
        kpis={kpis}
        accentColor={accentColor}
        theme={theme}
        valueFormatter={valueFormatter}
        chartType={chartType}
        metricKey={metricKey}
        orgId={orgId}
        filters={filters}
      />
    </>
  )
}