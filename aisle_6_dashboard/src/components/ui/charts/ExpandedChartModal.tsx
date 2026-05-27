"use client"

import KpiCard from "./KpiCard"
import { BarChartCard, LineChartCard, YoYBarChartCard } from "./ChartCards"
import type { MetricRow, KpiItem } from "./chartTypes"
import { formatNumber } from "./chartUtils"
import { useEffect, useState } from "react"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

type Theme = {
  surface: string
  line: string
  accent_color: string
  charcoal: string
}

type ExpandedChartModalProps = {
  open: boolean
  onClose: () => void
  sectionLabel: string

  data: MetricRow[]
  kpis: KpiItem[]

  accentColor: string
  theme: Theme

  valueFormatter?: (value: number) => string
  chartType?: "bar" | "line"

  metricKey: "units" | "buyers" | "velocity" | "pods"
  orgId: string | null
  filters: Record<string, string[]>
}

export default function ExpandedChartModal({
  open,
  onClose,
  sectionLabel,
  data,
  kpis,
  accentColor,
  theme,
  valueFormatter,
  chartType = "bar",
  metricKey,
  orgId,
  filters,
}: ExpandedChartModalProps) {
  const [expandedView, setExpandedView] =
    useState<"yoy" | "all_time">("yoy")

  const [chartData, setChartData] =
    useState<any[]>(data)

  const formatValue = (v: number) =>
    valueFormatter ? valueFormatter(v) : formatNumber(v)

  useEffect(() => {
    if (!open || !orgId) return

    const loadExpandedChart = async () => {
      try {
        const params = new URLSearchParams()

        params.set("org_id", orgId)
        params.set("metric", metricKey)
        params.set("view", expandedView)

        Object.entries(filters).forEach(([key, values]) => {
          values.forEach((value) => {
            params.append(key, value)
          })
        })

        const res = await fetch(
          `${API_BASE_URL}/overview/chart?${params.toString()}`
        )

        const json = await res.json()

        setChartData(Array.isArray(json) ? json : [])
      } catch (err) {
        console.error("Failed to load expanded chart", err)
      }
    }

    loadExpandedChart()
  }, [
    open,
    expandedView,
    metricKey,
    orgId,
    filters,
  ])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6"
      onClick={onClose}
    >
      <div
        className="flex h-[90vh] w-[92vw] flex-col rounded-[28px] bg-white p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-semibold">
            {sectionLabel}
          </h2>

          <button
            onClick={onClose}
            className="rounded-full border px-4 py-2 text-sm hover:bg-neutral-100"
          >
            Close
          </button>
        </div>

        {/* Body */}
        <div className="grid min-h-0 flex-1 grid-cols-[260px_1fr] gap-6 overflow-hidden">
          {/* KPI rail */}
          <aside className="space-y-3">
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
          </aside>

          {/* Chart area */}
          <section className="flex min-h-0 min-w-0 flex-col overflow-hidden">
            <div
              className="h-[calc(100%-56px)] overflow-hidden rounded-[24px] border p-4"
              style={{
                backgroundColor: "#FCFAF6",
                borderColor: "#EEE5D8",
              }}
            >
              <div
                className={
                  expandedView === "all_time"
                    ? "h-full overflow-x-auto overflow-y-hidden"
                    : "h-full overflow-hidden"
                }
              >
                <div
                  className={
                    expandedView === "all_time"
                      ? "h-full min-w-[1200px]"
                      : "h-full"
                  }
                >
                  {chartType === "line" ? (
                    <LineChartCard
                        data={chartData}
                        accentColor={accentColor}
                        theme={theme}
                        valueFormatter={valueFormatter}
                    />
                    ) : expandedView === "yoy" ? (
                    <YoYBarChartCard
                        data={chartData}
                        accentColor={accentColor}
                        valueFormatter={valueFormatter}
                        className="h-full"
                    />
                    ) : (
                    <BarChartCard
                        data={chartData}
                        accentColor={accentColor}
                        valueFormatter={valueFormatter}
                        className="h-full"
                    />
                    )}
                </div>
              </div>
            </div>

            {/* Toggle */}
            <div className="mt-3 flex h-11 shrink-0 gap-2">
              <button
                onClick={() => setExpandedView("yoy")}
                className={`rounded-full px-4 py-2 text-sm transition ${
                  expandedView === "yoy"
                    ? "bg-neutral-900 text-white"
                    : "border bg-white text-neutral-700"
                }`}
              >
                YoY
              </button>

              <button
                onClick={() => setExpandedView("all_time")}
                className={`rounded-full px-4 py-2 text-sm transition ${
                  expandedView === "all_time"
                    ? "bg-neutral-900 text-white"
                    : "border bg-white text-neutral-700"
                }`}
              >
                All-time
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}