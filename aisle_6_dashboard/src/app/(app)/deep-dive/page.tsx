"use client"

import { useEffect, useState } from "react"
import {
  Lightbulb,
  Target,
  AlertTriangle,
  TrendingUp,
} from "lucide-react"

import { useOrg } from "@/components/OrgContext"
import DeepDiveSnapshotSection, {
  DeepDiveSnapshotItem,
} from "@/components/deep-dive/DeepDiveSnapshotSection"
import LoadingScreen from "@/components/LoadingScreen"
import DashboardHeader from "@/components/ui/DashboardHeader"

import DistributionOpportunityDeepDive from "@/components/deep-dive/DistributionOpportunity"
import OverperformingChannelMomentum from "@/components/deep-dive/OverperformingChannelMomentum"
import ChainStruggling from "@/components/deep-dive/ChainStruggling"
import FailureToLaunch from "@/components/deep-dive/FailureToLaunch"
import DemoNarrative from "@/components/deep-dive/DemoNarrative"
import BusinessNarrativeSummary from "@/components/deep-dive/BusinessNarrative"

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

  sku?: string
  chain?: string
  channel?: string
  impact_units?: number
  launch_month_string?: string

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

const DEMO_ORG_ID = "839a67d6-7afa-4607-8524-8621184bfabc"

const theme = {
  surface: "#FCFAF6",
  line: "#EEE5D8",
  brown: "#705C4F",
  charcoal: "#343332",
}

const toneStyles = {
  positive: {
    bg: "#EAF3DE",
    text: "#3B6D11",
  },
  negative: {
    bg: "#FBF1EF",
    text: "#A06057",
  },
  neutral: {
    bg: "#F4F1EC",
    text: "#705C4F",
  },
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

function getInsightTone(
  insight: Insight
): "positive" | "negative" | "neutral" {
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
      style={{
        backgroundColor: "#FFFEFB",
        borderColor: theme.line,
      }}
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
        {insight.parts?.length
          ? renderParts(insight.parts)
          : insight.summary}
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
            {insight.key_points.map(
              (point: string, index: number) => (
                <li key={index} className="list-disc">
                  {point}
                </li>
              )
            )}
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

function SectionIcon({
  sectionKey,
}: {
  sectionKey: string
}) {
  if (sectionKey === "whats_working") {
    return <TrendingUp size={17} strokeWidth={2.2} />
  }

  if (sectionKey === "opportunities") {
    return <Target size={17} strokeWidth={2.2} />
  }

  if (sectionKey === "at_risk") {
    return <AlertTriangle size={17} strokeWidth={2.2} />
  }

  return <Lightbulb size={17} strokeWidth={2.2} />
}

export default function EmailPreviewPage() {
  const { org } = useOrg()

  const [data, setData] = useState<Digest | null>(null)

  const [snapshotCards, setSnapshotCards] = useState<
    DeepDiveSnapshotItem[]
  >([])

  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!org?.id) return

    async function load() {
      try {
        const url =
          `${process.env.NEXT_PUBLIC_API_BASE_URL}` +
          `/email/weekly-digest?org_id=${org.id}`

        const res = await fetch(url)

        if (!res.ok) {
          throw new Error(
            `Digest request failed: ${res.status}`
          )
        }

        const json = await res.json()
        setData(json)

      } catch (err: any) {
        console.error(err)
        setError(err.message)
      }
    }

    load()
  }, [org?.id])

  if (!org?.id) {
    return <div className="p-8">Missing org id.</div>
  }

  if (error) {
    return (
      <div className="p-8 text-red-600">
        Error: {error}
      </div>
    )
  }


  const sections = Array.isArray(data?.sections)
    ? data.sections
    : []

 return (
    <main className="min-h-screen bg-[#F6F2EA]">
      <DashboardHeader
        activePage="insights"
        dataThrough="August 2026"
        isStale={false}
      />

      <div className="ml-[238px] min-h-screen p-8">
        {!data ? (
          <LoadingScreen mode="results" />
        ) : (
          <div className="mx-auto max-w-7xl space-y-8">
            <div className="px-6 py-2">
              <div className="mx-auto max-w-5xl space-y-8">

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
                  style={{
                    backgroundColor: theme.surface,
                    borderColor: theme.line,
                  }}
                >
                  {/* SECTION HEADER */}

                  <div className="mb-4 flex items-center gap-3">
                    <div
                      className="flex h-9 w-9 items-center justify-center rounded-xl border"
                      style={{
                        backgroundColor: "#FFFDF9",
                        borderColor: theme.line,
                        color:
                          org?.primary_color ??
                          "#92B9DC",
                      }}
                    >
                      <SectionIcon
                        sectionKey={section.key}
                      />
                    </div>

                    <p
                      className="text-[16px] font-medium uppercase tracking-[0.18em]"
                      style={{ color: "#6B6B6B" }}
                    >
                      {section.title}
                    </p>
                  </div>

                  {/* SECTION CONTENT */}

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
                      const topMonthInsights =
                        section.insights.filter(
                          (i) =>
                            i.type === "top_month"
                        )

                      const otherInsights =
                        section.insights.filter(
                          (i) =>
                            i.type !== "top_month"
                        )

                      return (
                        <div className="space-y-3">
                          {/* TOP MONTH */}

                          {topMonthInsights.length >
                            0 && (
                            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                              {topMonthInsights.map(
                                (insight) => (
                                  <InsightCard
                                    key={`${section.key}-${insight.type}-${insight.summary}`}
                                    insight={insight}
                                  />
                                )
                              )}
                            </div>
                          )}

                          {/* EVERYTHING ELSE */}

                          {otherInsights.length > 0 &&
                            (section.key ===
                            "what_changed" ? (
                              org.id === DEMO_ORG_ID ? (
                                <DemoNarrative />
                              ) : (
                                <BusinessNarrativeSummary orgId={org.id} />
                              )
                            ) : (
                              <div className="grid grid-cols-1 gap-3">
                                {otherInsights.map(
                                  (
                                    insight,
                                    index
                                  ) => {
                                    /*
                                     * DISTRIBUTION OPPORTUNITY
                                     */

                                    if (
                                      insight.type ===
                                      "distribution_opportunity"
                                    ) {
                                      return (
                                        <DistributionOpportunityDeepDive
                                          key={`${section.key}-${insight.type}-${index}`}
                                          sku={
                                            insight.sku ??
                                            ""
                                          }
                                          chain={
                                            insight.chain ??
                                            ""
                                          }
                                          currentStores={
                                            insight
                                              .metrics
                                              ?.buying_stores
                                          }
                                          opportunityStores={
                                            insight
                                              .metrics
                                              ?.void_stores
                                          }
                                          annualizedOpportunityUnits={
                                            insight
                                              .metrics
                                              ?.impact_units
                                          }
                                          averageVelocity={
                                            insight
                                              .metrics
                                              ?.vpo_3m
                                          }
                                          carryingBrandUnits={
                                            insight
                                              .metrics
                                              ?.carrying_brand_units_per_store_3m
                                          }
                                          nonCarryingBrandUnits={
                                            insight
                                              .metrics
                                              ?.noncarrying_brand_units_per_store_3m
                                          }
                                          salesLiftPct={
                                            Number(
                                              insight
                                                .metrics
                                                ?.brand_units_lift_pct ??
                                                0
                                            ) * 100
                                          }
                                          drilldown={
                                            insight.drilldown
                                          }
                                          theme={
                                            theme
                                          }
                                        />
                                      )
                                    }

                                    /*
                                     * OVERPERFORMING CHANNEL
                                     */

                                    if (
                                      insight.type ===
                                      "overperforming_channel_momentum"
                                    ) {
                                      return (
                                        <OverperformingChannelMomentum
                                          key={`${section.key}-${insight.type}-${index}`}
                                          channel={
                                            insight
                                              .entities
                                              ?.channel ??
                                            ""
                                          }
                                          recentStoreShare={Number(
                                            insight
                                              .metrics
                                              ?.recent_store_share ??
                                              0
                                          )}
                                          recentUnitShare={Number(
                                            insight
                                              .metrics
                                              ?.recent_unit_share ??
                                              0
                                          )}
                                          returnOnDistributionIndex={Number(
                                            insight
                                              .metrics
                                              ?.return_on_distribution_index ??
                                              0
                                          )}
                                          velocityOutperformancePct={Number(
                                            insight
                                              .metrics
                                              ?.velocity_outperformance_pct ??
                                              0
                                          )}
                                          recentReorderRate={Number(
                                            insight
                                              .metrics
                                              ?.recent_3m_reorder_rate ??
                                              0
                                          )}
                                          unitShareChangeAbs={Number(
                                            insight
                                              .metrics
                                              ?.unit_share_change_abs ??
                                              0
                                          )}
                                          drilldown={
                                            insight.drilldown
                                          }
                                          theme={
                                            theme
                                          }
                                        />
                                      )
                                    }

                                    /*
                                     * CHAIN STRUGGLING
                                     */

                                    if (
                                      insight.type ===
                                      "chain_struggling"
                                    ) {
                                      return (
                                        <ChainStruggling
                                          key={`${section.key}-${insight.type}-${index}`}
                                          chain={
                                            insight
                                              .entities
                                              ?.chain ??
                                            ""
                                          }
                                          strugglingStores={Number(
                                            insight
                                              .metrics
                                              ?.struggling_stores ??
                                              0
                                          )}
                                          totalStores={Number(
                                            insight
                                              .metrics
                                              ?.total_stores ??
                                              0
                                          )}
                                          strugglingPct={Number(
                                            insight
                                              .metrics
                                              ?.struggling_pct ??
                                              0
                                          )}
                                          overallStrugglingPct={Number(
                                            insight
                                              .metrics
                                              ?.overall_struggling_pct ??
                                              0
                                          )}
                                          vsAverage={Number(
                                            insight
                                              .metrics
                                              ?.vs_avg ??
                                              0
                                          )}
                                          reorderRateCurrent={
                                            insight
                                              .metrics
                                              ?.reorder_rate_3m_current
                                          }
                                          reorderRatePrior={
                                            insight
                                              .metrics
                                              ?.reorder_rate_3m_prior_6m
                                          }
                                          reorderRateChange={
                                            insight
                                              .metrics
                                              ?.reorder_rate_3m_change_6m
                                          }
                                          drilldown={
                                            insight.drilldown
                                          }
                                          theme={
                                            theme
                                          }
                                        />
                                      )
                                    }

                                    /*
                                     * FAILURE TO LAUNCH
                                     */

                                    if (
                                      insight.type ===
                                      "failure_to_launch_new_store_risk"
                                    ) {
                                      return (
                                        <FailureToLaunch
                                          key={`${section.key}-${insight.type}-${index}`}
                                          chain={
                                            insight
                                              .entities
                                              ?.chain ??
                                            ""
                                          }
                                          launchMonth={
                                            insight.launch_month_string ??
                                            ""
                                          }
                                          launchedStores={Number(
                                            insight
                                              .metrics
                                              ?.launched_stores ??
                                              0
                                          )}
                                          launchedSkus={Number(
                                            insight
                                              .metrics
                                              ?.launched_skus ??
                                              0
                                          )}
                                          launchedPlacements={Number(
                                            insight
                                              .metrics
                                              ?.launched_placements ??
                                              0
                                          )}
                                          atRiskPlacements={Number(
                                            insight
                                              .metrics
                                              ?.at_risk_placements ??
                                              0
                                          )}
                                          reorderedPlacements={Number(
                                            insight
                                              .metrics
                                              ?.reordered_placements ??
                                              0
                                          )}
                                          atRiskRate={Number(
                                            insight
                                              .metrics
                                              ?.at_risk_rate ??
                                              0
                                          )}
                                          reorderRate={Number(
                                            insight
                                              .metrics
                                              ?.reorder_rate ??
                                              0
                                          )}
                                          avgInitialUnitsAtRisk={
                                            insight
                                              .metrics
                                              ?.avg_initial_units_at_risk
                                          }
                                          avgInitialUnitsReordered={
                                            insight
                                              .metrics
                                              ?.avg_initial_units_reordered
                                          }
                                          avgInitialUnitsGap={
                                            insight
                                              .metrics
                                              ?.avg_initial_units_gap
                                          }
                                          skuBreakdown={
                                            insight
                                              .metrics
                                              ?.sku_breakdown ??
                                            []
                                          }
                                          drilldown={
                                            insight.drilldown
                                          }
                                          theme={
                                            theme
                                          }
                                        />
                                      )
                                    }

                                    /*
                                     * DEFAULT INSIGHT
                                     */

                                    return (
                                      <InsightCard
                                        key={`${section.key}-${insight.type}-${index}`}
                                        insight={
                                          insight
                                        }
                                      />
                                    )
                                  }
                                )}
                              </div>
                            ))}
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

      )}

    </div>

  </main>
)
}