"use client"

import { useEffect, useState } from "react"
import { Lock } from "lucide-react"

import { useOrg } from "@/components/OrgContext"
import LoadingScreen from "@/components/LoadingScreen"

import DistributionOpportunity from "@/components/deep-dive/DistributionOpportunity"
import ChainStruggling from "@/components/deep-dive/ChainStruggling"
import FailureToLaunch from "@/components/deep-dive/FailureToLaunch"


type Insight = {
  type: string
  section?: string

  headline?: string
  summary?: string

  parts?: any[]
  description?: any[]
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
    title?: string
    subtitle?: string
    columns?: any[]
  }
}


type FreeTrialResponse = {
  available_months: number
  top_findings: Insight[]
  additional_findings_count: number
}


const theme = {
  surface: "#FCFAF6",
  line: "#EEE5D8",
  brown: "#705C4F",
  charcoal: "#343332",
}


function PlaceholderInsight({
  insight,
}: {
  insight: Insight
}) {
  return (
    <div
      className="rounded-[24px] border px-6 py-5"
      style={{
        backgroundColor: "#FFFEFB",
        borderColor: theme.line,
      }}
    >
      <p
        className="mb-2 text-[11px] font-medium uppercase tracking-[0.14em]"
        style={{ color: "#9A8A7C" }}
      >
        Finding
      </p>

      <p
        className="text-[18px] font-medium leading-snug"
        style={{ color: theme.charcoal }}
      >
        {insight.headline ??
          insight.summary ??
          "Finding detected"}
      </p>

      {insight.summary &&
        insight.summary !== insight.headline && (
          <p
            className="mt-2 text-[14px] leading-relaxed"
            style={{ color: theme.brown }}
          >
            {insight.summary}
          </p>
        )}

      <div
        className="mt-4 rounded-xl border px-4 py-3 text-[12px]"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.line,
          color: "#9A8A7C",
        }}
      >
        Detailed visualization coming soon.
      </div>
    </div>
  )
}


function FreeTrialInsight({
  insight,
  index,
}: {
  insight: Insight
  index: number
}) {
  if (insight.type === "distribution_opportunity") {
    return (
      <DistributionOpportunity
        key={`${insight.type}-${index}`}
        sku={insight.sku ?? ""}
        chain={insight.chain ?? ""}
        currentStores={insight.metrics?.buying_stores}
        opportunityStores={insight.metrics?.void_stores}
        annualizedOpportunityUnits={
          insight.metrics?.impact_units
        }
        averageVelocity={
          insight.metrics?.vpo_3m
        }
        carryingBrandUnits={
          insight.metrics?.carrying_brand_units_per_store_3m
        }
        nonCarryingBrandUnits={
          insight.metrics?.noncarrying_brand_units_per_store_3m
        }
        salesLiftPct={
          Number(
            insight.metrics?.brand_units_lift_pct ?? 0
          ) * 100
        }
        drilldown={insight.drilldown}
        theme={theme}
      />
    )
  }


  if (insight.type === "chain_struggling") {
    return (
      <ChainStruggling
        key={`${insight.type}-${index}`}
        chain={insight.entities?.chain ?? ""}
        strugglingStores={Number(
          insight.metrics?.struggling_stores ?? 0
        )}
        totalStores={Number(
          insight.metrics?.total_stores ?? 0
        )}
        strugglingPct={Number(
          insight.metrics?.struggling_pct ?? 0
        )}
        overallStrugglingPct={Number(
          insight.metrics?.overall_struggling_pct ?? 0
        )}
        vsAverage={Number(
          insight.metrics?.vs_avg ?? 0
        )}
        reorderRateCurrent={
          insight.metrics?.reorder_rate_3m_current
        }
        reorderRatePrior={
          insight.metrics?.reorder_rate_3m_prior_6m
        }
        reorderRateChange={
          insight.metrics?.reorder_rate_3m_change_6m
        }
        drilldown={insight.drilldown}
        theme={theme}
      />
    )
  }


  if (
    insight.type ===
    "failure_to_launch_new_store_risk"
  ) {
    return (
      <FailureToLaunch
        key={`${insight.type}-${index}`}
        chain={insight.entities?.chain ?? ""}
        launchMonth={
          insight.launch_month_string ?? ""
        }
        launchedStores={Number(
          insight.metrics?.launched_stores ?? 0
        )}
        launchedSkus={Number(
          insight.metrics?.launched_skus ?? 0
        )}
        launchedPlacements={Number(
          insight.metrics?.launched_placements ?? 0
        )}
        atRiskPlacements={Number(
          insight.metrics?.at_risk_placements ?? 0
        )}
        reorderedPlacements={Number(
          insight.metrics?.reordered_placements ?? 0
        )}
        atRiskRate={Number(
          insight.metrics?.at_risk_rate ?? 0
        )}
        reorderRate={Number(
          insight.metrics?.reorder_rate ?? 0
        )}
        avgInitialUnitsAtRisk={
          insight.metrics?.avg_initial_units_at_risk
        }
        avgInitialUnitsReordered={
          insight.metrics?.avg_initial_units_reordered
        }
        avgInitialUnitsGap={
          insight.metrics?.avg_initial_units_gap
        }
        skuBreakdown={
          insight.metrics?.sku_breakdown ?? []
        }
        drilldown={insight.drilldown}
        theme={theme}
      />
    )
  }


  if (
    insight.type === "dropoff_sku_risk" ||
    insight.type === "order_cadence_risk"
  ) {
    return (
      <PlaceholderInsight
        key={`${insight.type}-${index}`}
        insight={insight}
      />
    )
  }


  return (
    <PlaceholderInsight
      key={`${insight.type}-${index}`}
      insight={insight}
    />
  )
}


export default function FreeTrialPage() {
  const { org } = useOrg()

  const [data, setData] =
    useState<FreeTrialResponse | null>(null)

  const [error, setError] =
    useState<string | null>(null)


  useEffect(() => {
    if (!org?.id) return

    const currentOrgId = org.id

    async function load() {
      try {
        const url =
          `${process.env.NEXT_PUBLIC_API_BASE_URL}` +
          `/free-trial/insights?org_id=${encodeURIComponent(
            currentOrgId
          )}`

        const res = await fetch(url)

        if (!res.ok) {
          throw new Error(
            `Free trial request failed: ${res.status}`
          )
        }

        const json = await res.json()

        setData(json)
      } catch (err: any) {
        console.error(err)

        setError(
          err.message ??
            "Something went wrong loading your analysis."
        )
      }
    }

    load()
  }, [org?.id])


  if (!org?.id) {
    return <LoadingScreen />
  }


  if (error) {
    return (
      <main className="min-h-screen bg-[#F6F2EA] px-6 py-16">
        <div className="mx-auto max-w-3xl">
          <div
            className="rounded-[24px] border p-8"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.line,
            }}
          >
            <p
              className="text-[18px] font-medium"
              style={{ color: theme.charcoal }}
            >
              Something went wrong.
            </p>

            <p
              className="mt-2 text-[14px]"
              style={{ color: theme.brown }}
            >
              {error}
            </p>
          </div>
        </div>
      </main>
    )
  }


  if (!data) {
    return <LoadingScreen />
  }


  const findings =
    Array.isArray(data.top_findings)
      ? data.top_findings
      : []

  const totalFindings =
    findings.length +
    (data.additional_findings_count ?? 0)


  return (
    <main className="min-h-screen bg-[#F6F2EA]">
      <div className="mx-auto max-w-5xl px-6 py-14 md:py-18">
        {/* INTRO */}

        <section className="mx-auto mb-12 max-w-3xl text-center">
          <p
            className="mb-3 text-[12px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Your distributor data analysis
          </p>

          <h1
            className="text-[34px] font-semibold leading-[1.08] tracking-[-0.03em] md:text-[46px]"
            style={{ color: theme.charcoal }}
          >
            We found {totalFindings} things worth your attention.
          </h1>

          <p
            className="mx-auto mt-5 max-w-2xl text-[16px] leading-relaxed"
            style={{ color: theme.brown }}
          >
            SKUba analyzed {data.available_months} months of your
            distributor data to identify risks, opportunities,
            and changes across your business.
          </p>
        </section>


        {/* FINDINGS */}

        <section>
          <div className="mb-5">
            <p
              className="text-[12px] font-medium uppercase tracking-[0.16em]"
              style={{ color: "#9A8A7C" }}
            >
              Your analysis
            </p>

            <h2
              className="mt-1 text-[24px] font-semibold tracking-[-0.02em]"
              style={{ color: theme.charcoal }}
            >
              What needs your attention
            </h2>
          </div>


          {findings.length === 0 ? (
            <div
              className="rounded-[28px] border p-8"
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.line,
              }}
            >
              <p style={{ color: theme.brown }}>
                No major findings were identified in the available data.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {findings.map((insight, index) => (
                <FreeTrialInsight
                  key={`${insight.type}-${index}`}
                  insight={insight}
                  index={index}
                />
              ))}
            </div>
          )}
        </section>


        {/* LOCKED FINDINGS */}

        {data.additional_findings_count > 0 && (
          <section className="mt-8">
            <div
              className="rounded-[28px] border px-6 py-8 text-center md:px-10 md:py-10"
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.line,
              }}
            >
              <div
                className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border"
                style={{
                  backgroundColor: "#FFFEFB",
                  borderColor: theme.line,
                  color: theme.brown,
                }}
              >
                <Lock size={17} />
              </div>

              <h3
                className="mt-4 text-[21px] font-semibold tracking-[-0.02em]"
                style={{ color: theme.charcoal }}
              >
                {data.additional_findings_count} more{" "}
                {data.additional_findings_count === 1
                  ? "finding"
                  : "findings"}{" "}
                identified
              </h3>

              <p
                className="mx-auto mt-2 max-w-xl text-[14px] leading-relaxed"
                style={{ color: theme.brown }}
              >
                SKUba found additional risks and opportunities
                across your distributor data.
              </p>
            </div>
          </section>
        )}


        {/* PAID CTA */}

        <section className="mt-14">
          <div
            className="rounded-[32px] border px-7 py-10 text-center md:px-12 md:py-12"
            style={{
              backgroundColor: "#FFFEFB",
              borderColor: theme.line,
            }}
          >
            <p
              className="text-[12px] font-medium uppercase tracking-[0.16em]"
              style={{ color: "#9A8A7C" }}
            >
              Keep SKUba watching
            </p>

            <h2
              className="mx-auto mt-3 max-w-2xl text-[28px] font-semibold leading-tight tracking-[-0.03em]"
              style={{ color: theme.charcoal }}
            >
              Turn this snapshot into continuous monitoring.
            </h2>

            <p
              className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed"
              style={{ color: theme.brown }}
            >
              SKUba keeps analyzing your distributor data as your
              business changes, so you know what needs your attention
              without digging through reports yourself.
            </p>

            <button
              type="button"
              className="mt-7 rounded-full px-6 py-3 text-[14px] font-medium transition-opacity hover:opacity-90"
              style={{
                backgroundColor: theme.charcoal,
                color: "#FFFFFF",
              }}
              onClick={() => {
                // TODO:
                // Wire into paid conversion / onboarding flow.
                console.log("Upgrade")
              }}
            >
              Keep monitoring my business
            </button>
          </div>
        </section>
      </div>
    </main>
  )
}