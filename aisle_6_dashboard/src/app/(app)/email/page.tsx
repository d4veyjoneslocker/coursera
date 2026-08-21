"use client"

import { useEffect, useState } from "react"
import { Lightbulb, Target, AlertTriangle, TrendingUp } from "lucide-react"
import { useOrg } from "@/components/OrgContext"
import DeepDiveSnapshotSection, {DeepDiveSnapshotItem} from "@/components/deep-dive/DeepDiveSnapshotSection"
import LoadingScreen from "@/components/LoadingScreen";
import DashboardHeader from "@/components/ui/DashboardHeader"

type InsightPart =
  | {
      type: "text"
      value: string
    }

  | {
      type: "chip"
      value: string
      tone?: "positive" | "negative" | "neutral"
    }

  | {
      type: "metric_chip"
      value: string
      tone?: "positive" | "negative" | "neutral"
    }

  | {
      type: "sku_chip"
      value: string
    }

  | {
      type: "chain_chip"
      value: string
    }

type Insight = {
  type: string
  section?: string

  headline?: string
  summary?: string

  parts?: InsightPart[]
  description?: InsightPart[]
  key_points?: string[]

  metrics?: Record<string, any>
  entities?: Record<string, any>

  drilldown?: {
    label: string
    href: string
  }
}

type Section = {
  key: string
  title: string
  insights: Insight[]
}

type Digest = {
  subject?: string
  preview_text?: string
  sections?: Section[]
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

function formatInsightType(type: string) {
  const overrides: Record<string, string> = {
    failure_to_launch_new_store_risk: "Launch Monitoring",
  }

  if (overrides[type]) {
    return overrides[type]
  }

  return type
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function getInsightTone(insight: Insight): "positive" | "negative" | "neutral" {
  const chip = insight.parts?.find(
  (p) =>
    (p.type === "chip" || p.type === "metric_chip") &&
    p.tone !== "neutral"
) as Extract<InsightPart, { type: "chip" }> | undefined

  return chip?.tone ?? "neutral"
}

function NeutralChip({ value }: { value: string }) {
  return (
    <span
      className="inline-block items-center rounded px-1.5 py-0.5 text-[13px] font-medium uppercase tracking-wide"
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

function InsightCard({ insight }: { insight: any }) {
  const { skuColors } = useOrg()
  const tone = getInsightTone(insight)
  const styles = toneStyles[tone]

  const renderParts = (parts: any[]) => {
    return parts.map((part: any, index: number) => {
      const isLastPart = index === parts.length - 1
      const isTrailingValueChip =
        isLastPart &&
        part.type === "chip" &&
        part.tone === "positive" &&
        insight.type === "top_month"

      if (isTrailingValueChip) return null
      if (part.type === "text") {
        if (!part.value.trim()) return null

        return (
          <span key={index} className="mr-1">
            {part.value}
          </span>
        )
      }

      if (part.type === "sku_chip") {
        const skuColor = skuColors?.[part.value] || "#94A3B8"

        return (
          <span
            key={index}
            className="inline-block rounded-full px-2.5 py-1 text-[13px] font-medium"
            style={{
              backgroundColor: `${skuColor}20`,
              color: skuColor,
              border: `1px solid ${skuColor}40`,
            }}
          >
            {part.value}
          </span>
        )
      }

      if (part.type === "chain_chip") {
        return (
          <span
            key={index}
            className="inline-block items-center rounded-full px-2.5 py-1 text-[13px] font-medium"
            style={{
              backgroundColor: "#F4F1EC",
              color: theme.brown,
            }}
          >
            {part.value}
          </span>
        )
      }

      if (part.type === "chip" || part.type === "metric_chip") {
        const chipTone = (part.tone ?? "neutral") as
          | "positive"
          | "negative"
          | "neutral"

        const chipStyles = toneStyles[chipTone]

        return (
          <span
            key={index}
            className="inline-block items-center rounded-full px-2.5 py-1 text-[13px] font-medium"
            style={{
              backgroundColor: chipStyles.bg,
              color: chipStyles.text,
            }}
          >
            {part.value}
          </span>
        )
      }

      return null
    })
  }

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

      <p
        className="text-[16px] font-medium leading-relaxed"
        style={{ color: theme.brown }}
      >
        {insight.parts?.length ? renderParts(insight.parts) : insight.summary}
      </p>

      {insight.key_points?.length ? (
        <div
          className="mt-4 rounded-xl border px-4 py-3"
          style={{
            backgroundColor: "#FCFAF6",
            borderColor: theme.line,
          }}
        >
          <p
            className="mb-2 text-[11px] font-medium uppercase tracking-[0.14em]"
            style={{ color: "#9A8A7C" }}
          >
            Why it matters
          </p>

          <ul
            className="space-y-2 pl-4 text-[14px] leading-relaxed"
            style={{ color: theme.brown }}
          >
            {insight.key_points.map((point: string, index: number) => (
              <li key={index} className="list-disc">
                {point}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

            {insight.drilldown && (
              <div className="mt-4">
                <a
                  href={insight.drilldown.href}
                  className="inline-flex rounded-full border border-black/10 bg-[#F6F2EA] px-4 py-2 text-sm font-medium text-[#343332] hover:bg-[#E9E2C8]"
                >
                  {insight.drilldown.label} →
                </a>
              </div>
            )}
          </div>
        )
      }

function WhatChangedCard({ item }: { item: any }) {
  const { skuColors } = useOrg()

  const renderParts = (parts: any[]) => {
    return parts.map((part, index) => {
      if (part.type === "text") {
        return (
          <span key={index} className="mr-1">
            {part.value}
          </span>
        )
      }

      if (part.type === "sku_chip") {
        const skuColor =
          skuColors?.[part.value.trim().toUpperCase()] || "#94A3B8"

        return (
          <span
            key={index}
            className="mr-1 inline-block rounded-full px-2.5 py-1 text-[14px] font-medium"
            style={{
              backgroundColor: `${skuColor}20`,
              color: skuColor,
              border: `1px solid ${skuColor}40`,
            }}
          >
            {part.value}
          </span>
        )
      }

      if (part.type === "chain_chip") {
        return (
          <span
            key={index}
            className="mr-1 inline-block rounded-full px-2.5 py-1 text-[14px] font-medium"
            style={{
              backgroundColor: "#F4F1EC",
              color: theme.brown,
            }}
          >
            {part.value}
          </span>
        )
      }

      if (part.type === "state_chip") {
        return (
          <span
            key={index}
            className="mr-1 inline-block rounded-full px-2.5 py-1 text-[14px] font-medium"
            style={{
              backgroundColor: "#8B5CF620",
              color: "#8B5CF6",
              border: "1px solid #8B5CF640",
            }}
          >
            {part.value}
          </span>
        )
      }

      return null
    })
  }

  return (
    <div
      className="flex items-center justify-between gap-4 rounded-[16px] border px-5 py-4"
      style={{ backgroundColor: "#FFFEFB", borderColor: theme.line }}
    >
      <p className="text-[15px] font-medium leading-relaxed text-[#705C4F]">
        {item.parts?.length ? renderParts(item.parts) : item.headline}
      </p>

      {item.drilldown && (
        <a
          href={item.drilldown.href}
          className="shrink-0 rounded-full border border-black/10 bg-[#F6F2EA] px-3.5 py-1.5 text-xs font-medium text-[#343332] hover:bg-[#E9E2C8]"
        >
          {item.drilldown.label} →
        </a>
      )}
    </div>
  )
}

function SectionIcon({ sectionKey }: { sectionKey: string }) {
  if (sectionKey === "whats_working") return <TrendingUp size={17} strokeWidth={2.2} />
  if (sectionKey === "opportunities") return <Target size={17} strokeWidth={2.2} />
  if (sectionKey === "at_risk") return <AlertTriangle size={17} strokeWidth={2.2} />
  return <Lightbulb size={17} strokeWidth={2.2} />
}

export default function EmailPreviewPage() {
  const { org } = useOrg()
  const [data, setData] = useState<Digest | null>(null)
  const [snapshotCards, setSnapshotCards] = useState<DeepDiveSnapshotItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!org?.id) return

    async function load() {
      try {
        const url = `${process.env.NEXT_PUBLIC_API_BASE_URL}/email/weekly-digest?org_id=${org.id}`
        const res = await fetch(url)

        if (!res.ok) {
          throw new Error(`Digest request failed: ${res.status}`)
        }

        const json = await res.json()
        setData(json)

        const snapshotUrl =
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/email/deep-dive-snapshot?org_id=${org.id}`

        const snapshotRes = await fetch(snapshotUrl)

        if (!snapshotRes.ok) {
          throw new Error(`Snapshot request failed: ${snapshotRes.status}`)
        }

        const snapshotJson = await snapshotRes.json()

        setSnapshotCards(snapshotJson.cards ?? [])

      } catch (err: any) {
        console.error(err)
        setError(err.message)
      }
    }

    load()
  }, [org?.id])

  if (!org?.id) return <div className="p-8">Missing org id.</div>
  if (error) return <div className="p-8 text-red-600">Error: {error}</div>
  if (!data) return <LoadingScreen />;


  const sections = Array.isArray(data.sections) ? data.sections : []

  return (
      <main className="min-h-screen p-8 bg-[#F6F2EA]">
        <div className="mx-auto max-w-7xl space-y-8">
          <DashboardHeader
            activePage="insights"
            dataThrough="August 2026"
            isStale={false}
          />

      <div className="px-6 py-10">
        <div className="mx-auto max-w-5xl space-y-8">
        <header className="rounded-[32px] border border-black/10 bg-white p-7 shadow-[0_14px_34px_rgba(52,51,50,0.05)]">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#705C4F]">
            {org?.name}
          </p>

          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[#343332]">
            {data.subject ?? "Weekly Digest"}
          </h1>

          {data.preview_text && (
            <p className="mt-2 text-sm text-[#705C4F]">{data.preview_text}</p>
          )}
        </header>
        {/* TEMP DISABLED
        <DeepDiveSnapshotSection
          cards={snapshotCards}
          theme={{
            surface: "#FCFAF6",
            line: "#EEE5D8",
            accent_color: "#705C4F",
            charcoal: "#343332",
            primary_color: org?.primary_color,
            secondary_color: org?.secondary_color,
          }}
        />
        */}

        <div className="space-y-6">
          {sections.map((section) => (
            <section
              key={section.key}
              className="relative rounded-[32px] border p-5 shadow-[0_14px_34px_rgba(52,51,50,0.05)] md:p-6"
              style={{ backgroundColor: theme.surface, borderColor: theme.line }}
            >
              <div className="mb-4 flex items-center gap-3">
                <div
                  className="flex h-9 w-9 items-center justify-center rounded-xl border"
                  style={{
                    backgroundColor: "#FFFDF9",
                    borderColor: theme.line,
                    color: org?.primary_color ?? "#92B9DC",
                  }}
                >
                  <SectionIcon sectionKey={section.key} />
                </div>

                <p
                  className="text-[16px] font-medium uppercase tracking-[0.18em]"
                  style={{ color: "#6B6B6B" }}
                >
                  {section.title}
                </p>
              </div>

              {(section.insights ?? []).length === 0 ? (
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
                (() => {
                  const topMonthInsights = section.insights.filter(
                    (i) => i.type === "top_month"
                  )

                  const otherInsights = section.insights.filter(
                    (i) => i.type !== "top_month"
                  )

                  return (
                    <div className="space-y-3">
                      {topMonthInsights.length > 0 && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {topMonthInsights.map((insight) => (
                            <InsightCard
                              key={`${section.key}-${insight.type}-${insight.summary}`}
                              insight={insight}
                            />
                          ))}
                        </div>
                      )}

                      {otherInsights.length > 0 && (
                        section.key === "what_changed" ? (
                          <div className="grid grid-cols-1 gap-3">
                            {otherInsights.map((item, index) => (
                              <WhatChangedCard
                                key={`what-changed-${index}`}
                                item={item}
                              />
                            ))}
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 gap-3">
                            {otherInsights.map((insight, index) => (
                              <InsightCard
                                key={`${section.key}-${insight.type}-${index}`}
                                insight={insight}
                              />
                            ))}
                          </div>
                        )
                      )}
                    </div>
                  )
                })()
              )}
            </section>
          ))}
        </div>
      </div>
    </div>
    </div>
  </main>
)}