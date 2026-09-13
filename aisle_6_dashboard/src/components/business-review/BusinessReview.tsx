"use client"

import { useState } from "react"
import BusinessReviewHeader, {
  type ReviewComparison,
  type ReviewPeriod,
} from "@/components/business-review/BusinessReviewHeader"

import KpiCard from "@/components/ui/charts/KpiCard"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts"

type MetricRow = {
  metric: string
  label: string
  current: number | null
  comparison: number | null
  abs_change: number | null
  pct_change: number | null
}

type Story = {
  type: string
  headline: string
  detail?: string | null
  impact?: number | null
  driver_type?: string | null
  scope?: Record<string, string>
  visual?: Visual
}

type Visual =
  | {
      type: "bar_chart" | "horizontal_bar_chart"
      title: string
      metric?: string
      data: {
        label: string
        value: number
        velocity?: number
      }[]
    }
  | {
      type: "donut_chart" | "stacked_share_bar"
      title: string
      metric?: string
      data: {
        label: string
        value: number
        share?: number
      }[]
    }
  | {
      type: "progress_bar"
      title: string
      value: number
      label?: string
    }
  | {
      type: "benchmark_bar"
      metric?: string
      current: number
      benchmark: number
      title?: string
    }

type EntityMetric = {
  current: number | null
  comparison: number | null
  abs_change: number | null
  pct_change: number | null
}

type RankingRow = {
  chain?: string
  sku?: string
  customer_name?: string
  coded_customer?: string
  city?: string
  state?: string

  // Enriched retailer / product payload
  units?: EntityMetric
  buying_stores?: EntityMetric
  active_pods?: EntityMetric
  velocity?: EntityMetric
  reorder_rate?: EntityMetric

  // Store payload remains flat for now
  value_current?: number | null
  value_comparison?: number | null
  abs_change?: number | null
  pct_change?: number | null
  velocity_current?: number | null
  velocity_comparison?: number | null
  velocity_change?: number | null
}

type RankingSection = {
  top: RankingRow[]
  gainers: RankingRow[]
  decliners: RankingRow[]
  current_only: RankingRow[]
  lost: RankingRow[]
  visuals: Visual[]
}

type LaunchHealth = {
  value: number
  label: string
  supporting: {
    chain: string
    value: number
    headline: string
    detail?: string | null
  }[]
}

export type BusinessReviewData = {
  meta: {
    period: {
      label: string
      start: string
      end: string
    }
    comparison: {
      label: string
      start: string
      end: string
    }
  }

  hero: {
    headline: string
    summary: string
    highlight?: MetricRow
  }

  scorecard: MetricRow[]

  key_stories: {
    stories: Story[]
    visuals: Visual[]
  }

  inside_period?: {
    meta: {
      label: string
      current: {
        label: string
        start: string
        end: string
      }
      comparison: {
        label: string
        start: string
        end: string
      }
    }
    headline: string
    summary: string
    scorecard: MetricRow[]
    visuals: Visual[]
    launch_health?: LaunchHealth | null
    stories: Story[]
  } | null

  retailers: RankingSection
  products: RankingSection
  stores: RankingSection

  distribution: {
    summary: {
      buying_stores: number
      chains: number
      skus: number
      states: number
      dcs: number
    }
    visuals: Visual[]
  }

  additional_stories: Story[]
}

type DrilldownTab = "retailers" | "products" | "stores"

type Props = {
  data: BusinessReviewData
  period: ReviewPeriod
  year: number
  comparison: ReviewComparison
  years: number[]
  onPeriodChange: (period: ReviewPeriod) => void
  onYearChange: (year: number) => void
  onComparisonChange: (comparison: ReviewComparison) => void
}

export default function BusinessReview({
  data,
  period,
  year,
  comparison,
  years,
  onPeriodChange,
  onYearChange,
  onComparisonChange,
}: Props) {
  const [activeTab, setActiveTab] = useState<DrilldownTab>("retailers")

  function renderVisual(visual: Visual, key?: string | number) {
    if (visual.type === "bar_chart") {
      return (
        <div key={key} className="border-y border-neutral-200/80 py-5">
          <div className="mb-4 text-sm font-semibold text-neutral-700">
            {visual.title}
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={visual.data}>
                <XAxis
                  dataKey="label"
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />
                <Tooltip />
                <Bar
                  dataKey="value"
                  fill="#92B9DC"
                  radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )
    }

    if (visual.type === "horizontal_bar_chart") {
      return (
        <div key={key} className="border-y border-neutral-200/80 py-5">
          <div className="mb-4 text-sm font-semibold text-neutral-700">
            {visual.title}
          </div>

          <div
            className="w-full"
            style={{
              height: Math.max(260, visual.data.length * 36),
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={visual.data}
                layout="vertical"
                margin={{
                  left: 20,
                  right: 20,
                }}
              >
                <XAxis
                  type="number"
                  hide
                />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={160}
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                />
                <Tooltip />
                <Bar
                  dataKey="value"
                  fill="#92B9DC"
                  radius={[0, 8, 8, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )
    }

    if (visual.type === "donut_chart") {
      const total = visual.data.reduce(
        (sum, row) => sum + Math.abs(row.value),
        0
      )

      const colors = [
        "#92B9DC",
        "#F7B045",
        "#F8AAB9",
        "#705C4F",
      ]

      return (
        <div key={key} className="border-y border-neutral-200/80 py-5">
          <div className="mb-4 text-sm font-semibold text-neutral-700">
            {visual.title}
          </div>

          <div className="grid gap-4 md:grid-cols-[220px_1fr] md:items-center">
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={visual.data}
                    dataKey="value"
                    nameKey="label"
                    innerRadius={60}
                    outerRadius={86}
                    paddingAngle={2}
                  >
                    {visual.data.map((_, index) => (
                      <Cell
                        key={index}
                        fill={colors[index % colors.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-3">
              {visual.data.map((row, index) => (
                <div
                  key={row.label}
                  className="flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{
                        backgroundColor:
                          colors[index % colors.length],
                      }}
                    />
                    <span className="text-sm text-neutral-700">
                      {row.label}
                    </span>
                  </div>

                  <span className="text-sm font-semibold text-neutral-900">
                    {row.share != null
                      ? formatPercent(row.share)
                      : total
                        ? formatPercent(Math.abs(row.value) / total)
                        : "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )
    }

    if (visual.type === "stacked_share_bar") {
      const total = visual.data.reduce(
        (sum, row) => sum + Math.abs(row.value),
        0
      )

      return (
        <div key={key} className="border-y border-neutral-200/80 py-5">
          <div className="mb-4 text-sm font-semibold text-neutral-700">
            {visual.title}
          </div>

          <div className="flex h-4 overflow-hidden rounded-full bg-neutral-100">
            {visual.data.map((row, index) => {
              const share =
                row.share ?? (total ? Math.abs(row.value) / total : 0)

              const backgrounds = [
                "#92B9DC",
                "#F7B045",
                "#F8AAB9",
                "#705C4F",
              ]

              return (
                <div
                  key={row.label}
                  style={{
                    width: `${share * 100}%`,
                    backgroundColor:
                      backgrounds[index % backgrounds.length],
                  }}
                />
              )
            })}
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {visual.data.map((row) => (
              <div
                key={row.label}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-neutral-600">{row.label}</span>
                <span className="font-semibold text-neutral-900">
                  {formatPercent(
                    row.share ??
                      (total ? Math.abs(row.value) / total : 0)
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )
    }

    if (visual.type === "progress_bar") {
      return (
        <div key={key} className="border-y border-neutral-200/80 py-5">
          <div className="text-sm font-semibold text-neutral-700">
            {visual.title}
          </div>

          <div className="mt-4 text-4xl font-semibold tracking-tight text-neutral-950">
            {formatPercent(visual.value)}
          </div>

          {visual.label && (
            <div className="mt-1 text-sm text-neutral-500">
              {visual.label}
            </div>
          )}

          <div className="mt-5 h-3 overflow-hidden rounded-full bg-neutral-100">
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.min(visual.value * 100, 100)}%`,
                backgroundColor: "#92B9DC",
              }}
            />
          </div>
        </div>
      )
    }

    if (visual.type === "benchmark_bar") {
      const max = Math.max(
        visual.current,
        visual.benchmark,
        0.0001
      )

      return (
        <div key={key} className="border-y border-neutral-200/80 py-5">
          <div className="text-sm font-semibold text-neutral-700">
            {visual.title ?? "Velocity benchmark"}
          </div>

          <div className="mt-5 space-y-4">
            <BenchmarkRow
              label="Current"
              value={visual.current}
              max={max}
            />

            <BenchmarkRow
              label="Benchmark"
              value={visual.benchmark}
              max={max}
            />
          </div>
        </div>
      )
    }

    return null
  }

  const primaryStories = data.key_stories.stories.slice(0, 3)
  const momentumVisual = data.inside_period?.visuals?.[0]
  const extraSignals = data.additional_stories.slice(0, 3)

  return (
    <div className="min-h-screen bg-[#FBFAF8] text-neutral-950">
      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-12 lg:py-12">
        {/* HEADER */}
        <BusinessReviewHeader
          period={period}
          year={year}
          comparison={comparison}
          years={years}
          headline={data.hero.headline}
          summary={data.hero.summary}
          comparisonLabel={data.meta.comparison.label}
          onPeriodChange={onPeriodChange}
          onYearChange={onYearChange}
          onComparisonChange={onComparisonChange}
        />

        {/* SCORECARD */}
        <section className="border-y border-neutral-200/80 py-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {data.scorecard.map((metric) => (
              <KpiCard
                key={metric.metric}
                title={metric.label}
                value={formatMetricValue(metric.metric, metric.current)}
                sideValue={metric.pct_change ?? undefined}
                sideLabel="vs comparison"
                sideType="percent"
                theme={{
                  accent_color: "#705C4F",
                  charcoal: "#343332",
                }}
              />
            ))}
          </div>
        </section>

        {/* WHAT MATTERED */}
        <section className="mx-auto max-w-5xl py-14 lg:py-20">
          <div className="grid gap-10 lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-16">
            <div>
              <SectionEyebrow>What mattered</SectionEyebrow>
              <p className="mt-3 max-w-[220px] text-sm leading-6 text-neutral-400">
                The few changes that best explain the period.
              </p>
            </div>

            <div className="divide-y divide-neutral-200/80 border-y border-neutral-200/80">
              {primaryStories.map((story, index) => (
                <EditorialStory
                  key={`${story.headline}-${index}`}
                  story={story}
                  index={index + 1}
                />
              ))}

              {primaryStories.length === 0 && (
                <div className="py-8 text-sm text-neutral-400">
                  No major stories surfaced for this period.
                </div>
              )}
            </div>
          </div>
        </section>

        {/* MOMENTUM */}
        {data.inside_period && (
          <section className="border-t border-neutral-200/80 py-14 lg:py-20">
            <div className="mx-auto max-w-5xl">
              <div className="grid gap-10 lg:grid-cols-[1fr_0.9fr] lg:items-start lg:gap-16">
                <div>
                  <div className="flex items-center gap-3">
                    <SectionEyebrow>Momentum</SectionEyebrow>
                    <span className="text-xs text-neutral-300">
                      {data.inside_period.meta.label}
                    </span>
                  </div>

                  <h2 className="mt-5 max-w-xl text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">
                    {data.inside_period.headline}
                  </h2>

                  <p className="mt-4 max-w-xl text-base leading-7 text-neutral-500">
                    {data.inside_period.summary}
                  </p>

                  {data.inside_period.launch_health && (
                    <div className="mt-8 flex items-end gap-5 border-l-2 border-[#92B9DC] pl-5">
                      <div>
                        <div className="text-xs font-medium uppercase tracking-[0.16em] text-neutral-400">
                          Recent-launch reorder health
                        </div>
                        <div className="mt-2 text-4xl font-semibold tracking-[-0.04em]">
                          {formatPercent(data.inside_period.launch_health.value)}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {momentumVisual && (
                  <div className="min-w-0">
                    {renderVisual(momentumVisual, "momentum")}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* DEEP DIVE */}
        <section className="border-t border-neutral-200/80 py-14 lg:py-20">
          <div className="mx-auto max-w-6xl">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <SectionEyebrow>Deep dive</SectionEyebrow>
                <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em]">
                  Explore the business
                </h2>
              </div>

              <div className="flex flex-wrap gap-1 rounded-xl bg-neutral-100/80 p-1">
                {(
                  [
                    ["retailers", "Retailers"],
                    ["products", "Products"],
                    ["stores", "Stores"],
                  ] as [DrilldownTab, string][]
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setActiveTab(value)}
                    className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                      activeTab === value
                        ? "bg-white text-neutral-950 shadow-sm"
                        : "text-neutral-500 hover:text-neutral-900"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-8">
              {activeTab === "retailers" && (
                <DeepDiveRanking
                  data={data.retailers}
                  getLabel={(row) => row.chain ?? "Unknown"}
                  renderVisual={renderVisual}
                  cohortLabel="retailers"
                />
              )}

              {activeTab === "products" && (
                <DeepDiveRanking
                  data={data.products}
                  getLabel={(row) => row.sku ?? "Unknown"}
                  renderVisual={renderVisual}
                  cohortLabel="products"
                />
              )}

              {activeTab === "stores" && (
                <DeepDiveRanking
                  data={data.stores}
                  getLabel={(row) =>
                    row.customer_name ??
                    row.coded_customer ??
                    "Unknown"
                  }
                  renderVisual={renderVisual}
                  showVelocity
                  cohortLabel="stores"
                />
              )}
            </div>
          </div>
        </section>

        {/* SECONDARY SIGNALS */}
        {extraSignals.length > 0 && (
          <section className="border-t border-neutral-200/80 py-14">
            <div className="mx-auto max-w-5xl">
              <div className="grid gap-10 lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-16">
                <div>
                  <SectionEyebrow>Also worth noting</SectionEyebrow>
                </div>

                <div className="divide-y divide-neutral-200/80 border-t border-neutral-200/80">
                  {extraSignals.map((story, index) => (
                    <div
                      key={`${story.headline}-${index}`}
                      className="py-5"
                    >
                      <StoryCard story={story} bare />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

function SectionEyebrow({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#705C4F]">
      {children}
    </div>
  )
}

function StoryCard({
  story,
  featured = false,
  bare = false,
}: {
  story: Story
  featured?: boolean
  bare?: boolean
}) {
  const content = (
    <>
      <div className="flex items-start justify-between gap-4">
        <h3
          className={
            featured
              ? "text-xl font-semibold tracking-tight"
              : "text-base font-semibold"
          }
        >
          {story.headline}
        </h3>

        {story.impact != null && (
          <div className="shrink-0 text-sm font-semibold text-neutral-500">
            {formatSignedNumber(story.impact)}
          </div>
        )}
      </div>

      {story.detail && (
        <p className="mt-2 text-sm leading-6 text-neutral-500">
          {story.detail}
        </p>
      )}
    </>
  )

  if (bare) return content

  return (
    <div
      className={
        featured
          ? "rounded-3xl bg-[#92B9DC]/15 p-6"
          : "rounded-2xl bg-white p-5 shadow-sm ring-1 ring-black/5"
      }
    >
      {content}
    </div>
  )
}

function EditorialStory({
  story,
  index,
}: {
  story: Story
  index: number
}) {
  return (
    <div className="grid gap-4 py-7 sm:grid-cols-[36px_minmax(0,1fr)_auto] sm:items-start">
      <div className="pt-0.5 text-sm font-medium text-neutral-300">
        {String(index).padStart(2, "0")}
      </div>

      <div className="min-w-0">
        <h3 className="text-lg font-semibold leading-6 tracking-[-0.02em]">
          {story.headline}
        </h3>

        {story.detail && (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-neutral-500">
            {story.detail}
          </p>
        )}
      </div>

      {story.impact != null && (
        <div className="text-sm font-semibold tabular-nums text-neutral-700">
          {formatSignedNumber(story.impact)}
        </div>
      )}
    </div>
  )
}

function DeepDiveRanking({
  data,
  getLabel,
  renderVisual,
  showVelocity = false,
  cohortLabel = "entities",
}: {
  data: RankingSection
  getLabel: (row: RankingRow) => string
  renderVisual: (
    visual: Visual,
    key?: string | number
  ) => React.ReactNode
  showVelocity?: boolean
  cohortLabel?: string
}) {
  const rows = data.top.slice(0, 10)
  const isEnriched = rows.some((row) => row.units != null)

  const [metric, setMetric] = useState<
    "units" | "active_pods" | "velocity" | "reorder_rate"
  >("units")

  if (!isEnriched) {
    return (
      <StoreBreakdown
        rows={rows}
        getLabel={getLabel}
        visual={data.visuals[0]}
        renderVisual={renderVisual}
        showVelocity={showVelocity}
      />
    )
  }

  const metricOptions = [
    { key: "units", label: "Units" },
    { key: "active_pods", label: "PODs" },
    { key: "velocity", label: "VPO" },
    { key: "reorder_rate", label: "Reorder" },
  ] as const

  const selected =
    metricOptions.find((option) => option.key === metric) ??
    metricOptions[0]

  // Keep the cohort fixed to the top 10 by units, then re-rank those
  // important entities by the selected metric.
  const metricRows = [...rows]
    .filter((row) => row[metric]?.current != null)
    .sort(
      (a, b) =>
        (b[metric]?.current ?? -Infinity) -
        (a[metric]?.current ?? -Infinity)
    )

  const entityLabel =
    cohortLabel === "products"
      ? "products"
      : cohortLabel === "stores"
        ? "stores"
        : "retailers"

  const rowLabel =
    cohortLabel === "products"
      ? "Product"
      : cohortLabel === "stores"
        ? "Store"
        : "Retailer"

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.15em] text-[#705C4F]">
            Top 10 {entityLabel} by units
            {metric !== "units" && (
              <span className="font-normal text-neutral-400">
                {" "}· sorted by {selected.label}
              </span>
            )}
          </div>

          <p className="mt-1 max-w-xl text-[13px] leading-5 text-neutral-500">
            Focus on the highest-volume {entityLabel}, then switch metrics to
            compare their distribution, velocity, and reorder health.
          </p>
        </div>

        <div className="flex w-fit flex-wrap gap-1 rounded-xl bg-neutral-100/80 p-1">
          {metricOptions.map((option) => {
            const active = metric === option.key

            return (
              <button
                key={option.key}
                type="button"
                onClick={() => setMetric(option.key)}
                className={`rounded-lg px-3 py-2 text-xs font-medium transition ${
                  active
                    ? "bg-white text-neutral-950 shadow-sm"
                    : "text-neutral-500 hover:text-neutral-900"
                }`}
              >
                {option.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="overflow-hidden border-y border-neutral-200/80">
        <div className="hidden grid-cols-[minmax(210px,1.55fr)_repeat(4,minmax(95px,0.75fr))] px-4 py-3 md:grid">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-neutral-400">
            {rowLabel}
          </div>

          {metricOptions.map((option) => (
            <div
              key={option.key}
              className={`text-right text-[10px] font-semibold uppercase tracking-[0.14em] ${
                metric === option.key
                  ? "text-[#699BC7]"
                  : "text-neutral-400"
              }`}
            >
              {option.label}
            </div>
          ))}
        </div>

        <div className="divide-y divide-neutral-200/80">
          {metricRows.map((row, index) => (
            <EntityMetricRow
              key={`${getLabel(row)}-${index}`}
              row={row}
              label={getLabel(row)}
              selectedMetric={metric}
            />
          ))}

          {metricRows.length === 0 && (
            <div className="px-4 py-10 text-sm text-neutral-400">
              No {selected.label.toLowerCase()} data is available for these
              top 10 {entityLabel} by units.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function EntityMetricRow({
  row,
  label,
  selectedMetric,
}: {
  row: RankingRow
  label: string
  selectedMetric:
    | "units"
    | "active_pods"
    | "velocity"
    | "reorder_rate"
}) {
  const cells = [
    {
      key: "units" as const,
      label: "Units",
      metric: row.units,
      value: formatCompactNumber(row.units?.current),
      change: formatEntityMetricChange(row.units, "number"),
    },
    {
      key: "active_pods" as const,
      label: "PODs",
      metric: row.active_pods,
      value: formatCompactNumber(row.active_pods?.current),
      change: formatEntityMetricChange(row.active_pods, "percent"),
    },
    {
      key: "velocity" as const,
      label: "VPO",
      metric: row.velocity,
      value:
        row.velocity?.current == null
          ? "—"
          : formatNumber(row.velocity.current, 2),
      change: formatEntityMetricChange(row.velocity, "percent"),
    },
    {
      key: "reorder_rate" as const,
      label: "Reorder",
      metric: row.reorder_rate,
      value:
        row.reorder_rate?.current == null
          ? "—"
          : formatPercent(row.reorder_rate.current),
      change: formatEntityMetricChange(row.reorder_rate, "points"),
    },
  ]

  return (
    <div className="grid gap-3 px-4 py-[18px] md:grid-cols-[minmax(210px,1.55fr)_repeat(4,minmax(95px,0.75fr))] md:items-center md:gap-0">
      <div className="min-w-0 pr-6">
        <div className="truncate text-[13px] font-semibold text-neutral-900">
          {label}
        </div>
      </div>

      {cells.map((cell) => {
        const selected = selectedMetric === cell.key

        const rawChange =
          cell.key === "reorder_rate"
            ? cell.metric?.abs_change
            : cell.key === "units"
              ? cell.metric?.abs_change
              : cell.metric?.pct_change

        const positive = (rawChange ?? 0) > 0
        const negative = (rawChange ?? 0) < 0

        return (
          <div
            key={cell.key}
            className="px-2 text-left md:px-3 md:text-right"
          >
            <div className="text-[9px] font-semibold uppercase tracking-[0.12em] text-neutral-400 md:hidden">
              {cell.label}
            </div>

            <div
              className={`mt-1 tabular-nums md:mt-0 ${
                selected
                  ? "text-[16px] font-semibold text-[#4F7FA8]"
                  : "text-[13px] font-medium text-neutral-600"
              }`}
            >
              {cell.value}
            </div>

            {selected && (
              <div
                className={`mt-1 text-[9px] font-medium ${
                  positive
                    ? "text-emerald-700"
                    : negative
                      ? "text-rose-700"
                      : "text-neutral-400"
                }`}
              >
                {cell.change}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}


function formatEntityMetricChange(
  metric: EntityMetric | undefined,
  mode: "number" | "percent" | "points"
) {
  if (!metric) return "No data"

  if (metric.comparison == null && metric.current != null) {
    return "New"
  }

  if (mode === "number") {
    if (metric.abs_change == null) return "No comparison"
    return formatSignedCompactNumber(metric.abs_change)
  }

  if (mode === "points") {
    if (metric.abs_change == null) return "No comparison"
    const points = metric.abs_change * 100
    return `${points > 0 ? "+" : ""}${points.toFixed(1)} pts`
  }

  if (metric.pct_change == null) return "No comparison"

  return `${metric.pct_change > 0 ? "+" : ""}${(
    metric.pct_change * 100
  ).toFixed(1)}%`
}


function StoreBreakdown({
  rows,
  getLabel,
  visual,
  renderVisual,
  showVelocity,
}: {
  rows: RankingRow[]
  getLabel: (row: RankingRow) => string
  visual?: Visual
  renderVisual: (
    visual: Visual,
    key?: string | number
  ) => React.ReactNode
  showVelocity: boolean
}) {
  return (
    <div className="overflow-hidden border-y border-neutral-200/80">
      <div className="grid grid-cols-[minmax(0,1fr)_auto] px-4 py-3">
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-neutral-400">
          Store
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#699BC7]">
          Units
        </span>
      </div>

      <div className="divide-y divide-neutral-200/80">
        {rows.map((row, index) => (
          <div
            key={`${getLabel(row)}-${index}`}
            className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-6 px-4 py-[18px]"
          >
            <div className="min-w-0">
              <div className="truncate text-[13px] font-semibold text-neutral-900">
                {getLabel(row)}
              </div>

              {showVelocity && row.velocity_current != null && (
                <div className="mt-1 text-[10px] text-neutral-400">
                  {formatNumber(row.velocity_current, 2)} VPO
                </div>
              )}
            </div>

            <div className="text-right">
              <div className="text-[16px] font-semibold tabular-nums text-[#4F7FA8]">
                {formatCompactNumber(row.value_current)}
              </div>

              <div
                className={`mt-1 text-[9px] font-medium ${
                  (row.abs_change ?? 0) > 0
                    ? "text-emerald-700"
                    : (row.abs_change ?? 0) < 0
                      ? "text-rose-700"
                      : "text-neutral-400"
                }`}
              >
                {row.abs_change == null
                  ? "New this period"
                  : `${formatSignedCompactNumber(row.abs_change)} vs comparison`}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


function formatEntityChange(
  metric: EntityMetric | undefined,
  noun: string
) {
  if (!metric) return `No ${noun} data`

  if (metric.comparison == null && metric.current != null) {
    return "New this period"
  }

  if (metric.abs_change == null) {
    return "No comparison"
  }

  return `${formatSignedCompactNumber(metric.abs_change)} vs comparison`
}


function DistributionPanel({
  summary,
}: {
  summary: BusinessReviewData["distribution"]["summary"]
}) {
  const rows = [
    ["Buying stores", summary.buying_stores],
    ["Chains", summary.chains],
    ["SKUs", summary.skus],
    ["States", summary.states],
    ["DCs", summary.dcs],
  ] as const

  return (
    <div className="grid border-y border-neutral-200 sm:grid-cols-2 lg:grid-cols-5">
      {rows.map(([label, value]) => (
        <div
          key={label}
          className="py-7 sm:px-5 lg:border-r lg:border-neutral-200 lg:first:pl-0 lg:last:border-r-0"
        >
          <div className="text-xs text-neutral-400">{label}</div>
          <div className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
            {formatNumber(value)}
          </div>
        </div>
      ))}
    </div>
  )
}

function RankingSection({
  title,
  data,
  getLabel,
  renderVisual,
  showVelocity = false,
}: {
  title: string
  data: RankingSection
  getLabel: (row: RankingRow) => string
  renderVisual: (
    visual: Visual,
    key?: string | number
  ) => React.ReactNode
  showVelocity?: boolean
}) {
  return (
    <section className="border-b border-neutral-200 py-12">
      <SectionEyebrow>{title}</SectionEyebrow>

      <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_0.9fr]">
        <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-black/5">
          {data.top.slice(0, 10).map((row, index) => (
            <div
              key={`${getLabel(row)}-${index}`}
              className="flex items-center justify-between gap-5 border-b border-neutral-100 px-5 py-4 last:border-b-0"
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">
                  {getLabel(row)}
                </div>

                {showVelocity &&
                  row.velocity_current != null && (
                    <div className="mt-1 text-xs text-neutral-400">
                      Velocity{" "}
                      {formatNumber(row.velocity_current, 2)}
                    </div>
                  )}
              </div>

              <div className="shrink-0 text-right">
                <div className="text-sm font-semibold">
                  {formatNumber(row.value_current)}
                </div>

                <div className="mt-1 text-xs text-neutral-400">
                  {row.abs_change == null
                    ? "New"
                    : formatSignedNumber(row.abs_change)}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          {data.visuals.map((visual, index) =>
            renderVisual(visual, index)
          )}
        </div>
      </div>
    </section>
  )
}

function FootprintMetric({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-black/5">
      <div className="text-xs text-neutral-400">{label}</div>
      <div className="mt-2 text-2xl font-semibold">
        {formatNumber(value)}
      </div>
    </div>
  )
}

function BenchmarkRow({
  label,
  value,
  max,
}: {
  label: string
  value: number
  max: number
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-neutral-500">{label}</span>
        <span className="font-semibold">
          {formatNumber(value, 2)}
        </span>
      </div>

      <div className="h-3 overflow-hidden rounded-full bg-neutral-100">
        <div
          className="h-full rounded-full"
          style={{
            width: `${(value / max) * 100}%`,
            backgroundColor:
              label === "Current"
                ? "#92B9DC"
                : "#705C4F",
          }}
        />
      </div>
    </div>
  )
}

function formatMetricValue(
  metric: string,
  value: number | null
) {
  if (value == null) return "—"

  if (
    metric === "reorder_rate"
  ) {
    return formatPercent(value)
  }

  if (metric === "velocity") {
    return formatNumber(value, 2)
  }

  return formatNumber(value)
}

function formatChange(metric: MetricRow) {
  if (metric.pct_change == null) {
    return "No comparison"
  }

  const sign = metric.pct_change > 0 ? "+" : ""

  return `${sign}${formatPercent(metric.pct_change)} vs comparison`
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

function formatNumber(
  value: number | null | undefined,
  decimals = 0
) {
  if (value == null) return "—"

  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

function formatCompactNumber(
  value: number | null | undefined
) {
  if (value == null) return "—"

  const abs = Math.abs(value)

  if (abs >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}M`
  }

  if (abs >= 1_000) {
    return `${(value / 1_000).toFixed(abs >= 100_000 ? 0 : 1)}K`
  }

  return formatNumber(value)
}

function formatSignedCompactNumber(
  value: number | null | undefined
) {
  if (value == null) return "—"
  return `${value > 0 ? "+" : ""}${formatCompactNumber(value)}`
}

function formatSignedNumber(
  value: number | null | undefined
) {
  if (value == null) return "—"

  const sign = value > 0 ? "+" : ""

  return `${sign}${formatNumber(value)}`
}