"use client"

import { useEffect, useMemo, useState } from "react"
import { Lightbulb, Target } from "lucide-react"

type InsightPart =
  | { type: "text"; value: string }
  | { type: "chip"; value: string; tone?: "positive" | "negative" | "neutral" }

type Insight = {
  type: string
  summary: string
  parts?: InsightPart[]
}

type InsightsSectionProps = {
  orgId: string | null
  filters: Record<string, string | string[] | undefined | null>
  endpoint: "overview" | "store-health"
  brandPrimary?: string
  brandPrimaryBg?: string
  brandSecondary?: string
  brandSecondaryBg?: string
}

const theme = {
  surface: "#FCFAF6",
  line: "#EEE5D8",
  brown: "#705C4F",
  charcoal: "#343332",
}

const toneStyles = {
  positive: { bg: "#EAF3DE", text: "#3B6D11" },
  negative: { bg: "#FBF1EF", text: "#A06057" },
  neutral: { bg: "#F4F1EC", text: "#705C4F" },
}

const OPPORTUNITY_TYPES = new Set(["distribution_opportunity"])

function getInsightTone(insight: Insight): "positive" | "negative" | "neutral" {
  const chip = insight.parts?.find(
    (p) => p.type === "chip" && p.tone !== "neutral"
  ) as Extract<InsightPart, { type: "chip" }> | undefined

  return chip?.tone ?? "neutral"
}

function formatInsightType(type: string) {
  return type
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function NeutralChip({ value }: { value: string }) {
  return (
    <span
      className="inline-flex items-center rounded px-1.5 py-0.5 text-[13px] font-medium uppercase tracking-wide"
      style={{
        backgroundColor: "#F4F1EC",
        border: "0.5px solid #E7DED2",
        color: theme.brown,
      }}
    >
      {value}
    </span>
  )
}

function OpportunityCard({
  insight,
  brandSecondary,
  brandSecondaryBg,
}: {
  insight: Insight
  brandSecondary: string
  brandSecondaryBg: string
}) {
  return (
    <div
      className="rounded-[16px] border px-6 py-5 transition-all"
      style={{ backgroundColor: "#FFFEFB", borderColor: theme.line }}
    >
      <p
        className="mb-2 text-xs uppercase tracking-[0.12em] leading-tight"
        style={{ color: theme.brown }}
      >
        {formatInsightType(insight.type)}
      </p>

      <p className="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-[15px] leading-snug">
        {insight.parts?.length
          ? insight.parts.map((part, index) => {
              if (part.type === "text") {
                if (!part.value.trim()) return null
                return (
                  <span key={index} style={{ color: theme.brown }}>
                    {part.value.trim()}
                  </span>
                )
              }

              if (part.tone === "neutral") {
                return <NeutralChip key={index} value={part.value} />
              }

              return (
                <span
                  key={index}
                  className="text-[19px] font-medium"
                  style={{ color: theme.charcoal }}
                >
                  {part.value}
                </span>
              )
            })
          : insight.summary}
      </p>

      <div className="mt-3">
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[13px] font-medium"
          style={{
            backgroundColor: brandSecondaryBg,
            color: brandSecondary,
          }}
        >
          <Target size={13} strokeWidth={2.2} />
          Opportunity
        </span>
      </div>
    </div>
  )
}

function StandardCard({ insight }: { insight: Insight }) {
  const tone = getInsightTone(insight)
  const styles = toneStyles[tone]

  return (
    <div
      className="rounded-[16px] border px-6 py-5 transition-all"
      style={{ backgroundColor: "#FFFEFB", borderColor: theme.line }}
    >
      <p
        className="mb-2 text-xs uppercase tracking-[0.12em] leading-tight"
        style={{ color: theme.brown }}
      >
        {formatInsightType(insight.type)}
      </p>

      <p className="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-[15px] leading-snug">
        {insight.parts?.length
          ? (() => {
              let nonNeutralIdx = 0

              return insight.parts.map((part, index) => {
                if (part.type === "text") {
                  if (!part.value.trim()) return null
                  return (
                    <span key={index} style={{ color: theme.brown }}>
                      {part.value.trim()}
                    </span>
                  )
                }

                if (part.tone === "neutral") {
                  return <NeutralChip key={index} value={part.value} />
                }

                if (nonNeutralIdx++ === 0) {
                  return (
                    <span
                      key={index}
                      className="text-[19px] font-medium"
                      style={{ color: theme.charcoal }}
                    >
                      {part.value}
                    </span>
                  )
                }

                return null
              })
            })()
          : insight.summary}
      </p>

      {(() => {
        const deltaPart = insight.parts
          ?.filter((p) => p.type === "chip" && p.tone !== "neutral")
          .slice(-1)[0] as Extract<InsightPart, { type: "chip" }> | undefined

        if (!deltaPart) return null

        return (
          <div className="mt-3">
            <span
              className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-[13px] font-medium"
              style={{ backgroundColor: styles.bg, color: styles.text }}
            >
              {tone === "positive" ? (
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path
                    d="M2 8L8 2M8 2H3.8M8 2V6.2"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : tone === "negative" ? (
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path
                    d="M2 2L8 8M8 8H3.8M8 8V3.8"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : null}

              {deltaPart.value}
            </span>
          </div>
        )
      })()}
    </div>
  )
}

function InsightCard({
  insight,
  brandSecondary,
  brandSecondaryBg,
}: {
  insight: Insight
  brandSecondary: string
  brandSecondaryBg: string
}) {
  if (OPPORTUNITY_TYPES.has(insight.type)) {
    return (
      <OpportunityCard
        insight={insight}
        brandSecondary={brandSecondary}
        brandSecondaryBg={brandSecondaryBg}
      />
    )
  }

  return <StandardCard insight={insight} />
}

export function InsightsSection({
  orgId,
  filters,
  endpoint,
  brandPrimary = "#92B9DC",
  brandPrimaryBg = "#EAF3F9",
  brandSecondary = "#F7B045",
  brandSecondaryBg = "#FFF4E3",
}: InsightsSectionProps) {
  const [insights, setInsights] = useState<Insight[]>([])
  const [loading, setLoading] = useState(false)

  const hasTimeFilter = useMemo(() => {
    return Boolean(filters.year || filters.month || filters.month_year)
  }, [filters])

  useEffect(() => {
    async function fetchInsights() {
      if (!orgId) return

      setLoading(true)

      try {
        const params = new URLSearchParams()
        params.set("org_id", orgId)

        Object.entries(filters).forEach(([key, value]) => {
          if (!value) return

          if (Array.isArray(value)) {
            value.forEach((v) => v && params.append(key, String(v)))
          } else {
            params.set(key, String(value))
          }
        })

        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/insights/${endpoint}?${params.toString()}`
        )

        if (!res.ok) {
          const errorText = await res.text()
          console.error("Insights fetch failed:", res.status, errorText)
          throw new Error("Failed to fetch insights")
        }

        const data = await res.json()
        setInsights(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error("Failed to fetch insights:", err)
        setInsights([])
      } finally {
        setLoading(false)
      }
    }

    fetchInsights()
  }, [orgId, filters, endpoint])

  return (
    <section
      className="relative rounded-[32px] border p-5 shadow-[0_14px_34px_rgba(52,51,50,0.05)] md:p-6"
      style={{ backgroundColor: theme.surface, borderColor: theme.line }}
    >
      <div className="mb-4 flex items-center gap-3">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-xl border"
          style={{
            backgroundColor: "#FFFDF9", // back to neutral
            borderColor: theme.line,
            color: brandPrimary,        // only icon is branded
          }}
        >
          <Lightbulb size={17} strokeWidth={2.2} />
        </div>

        <p
          className="text-[16px] font-medium uppercase tracking-[0.18em]"
          style={{ color: "#6B6B6B" }}
        >
          Insights
        </p>
      </div>

      {loading ? (
        <div
          className="rounded-2xl border px-5 py-4 text-[13px]"
          style={{
            backgroundColor: "#FFFDF9", // back to neutral
            borderColor: theme.line,
            color: brandPrimary,        // only icon is branded
          }}
        >
          Loading insights...
        </div>
      ) : insights.length === 0 ? (
        <div
          className="rounded-2xl border px-5 py-4 text-[13px]"
          style={{
            backgroundColor: "#FFFDF9",
            borderColor: theme.line,
            color: theme.brown,
          }}
        >
          No major changes to flag right now.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {insights.map((insight) => (
            <InsightCard
              key={`${insight.type}-${insight.summary}`}
              insight={insight}
              brandSecondary={brandSecondary}
              brandSecondaryBg={brandSecondaryBg}
            />
          ))}
        </div>
      )}
    </section>
  )
}