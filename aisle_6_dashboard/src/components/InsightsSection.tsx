"use client"

import { useEffect, useState } from "react"

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
}

const theme = {
  surface: "#FCFAF6",
  line: "#EEE5D8",
  brown: "#705C4F",
  charcoal: "#343332",
}

function InlineInsightChip({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode
  tone?: "positive" | "negative" | "neutral"
}) {
  const chipStyles =
    tone === "positive"
      ? { bg: "#EEF6F0", border: "#D7E8DB", text: "#5F7F68" }
      : tone === "negative"
        ? { bg: "#FBF0F0", border: "#EEDADA", text: "#A06161" }
        : { bg: "#F4F1EC", border: "#E7DED2", text: "#705C4F" }

  return (
    <span
      className="mx-1.5 inline-flex items-center rounded-full border px-3 py-1.5 text-[17px] font-semibold leading-none tracking-[-0.02em]"
      style={{
        backgroundColor: chipStyles.bg,
        borderColor: chipStyles.border,
        color: chipStyles.text,
      }}
    >
      {children}
    </span>
  )
}

export function InsightsSection({ orgId, filters, endpoint }: InsightsSectionProps) {
  const [insights, setInsights] = useState<Insight[]>([])
  const [loading, setLoading] = useState(false)

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
        className="relative rounded-[28px] border px-6 py-6 shadow-[0_10px_30px_rgba(52,51,50,0.05)]"
        style={{
        backgroundColor: "#FFFDF9",
        borderColor: "#E5DDD0",
        }}
    >
        <div className="mb-5 flex items-center gap-3">
        <div className="h-[3px] w-10 rounded-full bg-[#F7B045]" />
        <p
            className="text-xs uppercase tracking-[0.2em]"
            style={{ color: theme.brown }}
        >
            Insights
        </p>
        </div>

        {loading ? (
        <p className="text-[18px]" style={{ color: theme.brown }}>
            Loading insights...
        </p>
        ) : insights.length === 0 ? (
        <p className="text-[18px]" style={{ color: theme.brown }}>
            No major changes to flag right now.
        </p>
        ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    {insights.map((insight) => (
        <div
        key={`${insight.type}-${insight.summary}`}
        className="rounded-[20px] border px-5 py-4"
        style={{
            backgroundColor: "#FFFEFB",
            borderColor: "#EEE5D8",
        }}
        >
        <p
            className="flex flex-wrap items-center text-[16px] font-medium leading-7 tracking-[-0.01em]"
            style={{ color: theme.charcoal }}
        >
            {insight.parts?.length
            ? insight.parts.map((part, index) => {
                if (part.type === "text") {
                    return <span key={index}>{part.value}</span>
                }

                return (
                    <InlineInsightChip key={index} tone={part.tone}>
                    {part.value}
                    </InlineInsightChip>
                )
                })
            : insight.summary}
        </p>
        </div>
    ))}
    </div>
    )}
  </section>
)}