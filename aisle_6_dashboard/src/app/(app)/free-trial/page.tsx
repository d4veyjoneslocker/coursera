"use client"

import { useEffect, useState } from "react"
import { Check, Lock } from "lucide-react"

import { useOrg } from "@/components/OrgContext"
import LoadingScreen from "@/components/LoadingScreen"
import { supabase } from "@/lib/supabase"

import DistributionOpportunity from "@/components/deep-dive/DistributionOpportunity"
import ChainStruggling from "@/components/deep-dive/ChainStruggling"
import FailureToLaunch from "@/components/deep-dive/FailureToLaunch"
import DropoffSkuRisk from "@/components/deep-dive/DropoffSkuRisk"
import OrderCadenceRisk from "@/components/deep-dive/OrderCadenceRisk"


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
  coral: "#EE6A4C",
  coralDark: "#D9532F",
  coralSoft: "#FCE8E1",
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


  if (insight.type === "dropoff_sku_risk") {
    return (
      <DropoffSkuRisk
        key={`${insight.type}-${index}`}
        sku={insight.entities?.sku ?? ""}
        affectedStores={Number(
          insight.metrics?.affected_stores ?? 0
        )}
        affectedStoreShare={Number(
          insight.metrics?.affected_store_share ?? 0
        )}
        totalRecentBrandStores={Number(
          insight.metrics?.total_recent_brand_stores ?? 0
        )}
        prior3mSkuUnits={Number(
          insight.metrics?.prior_3m_sku_units ?? 0
        )}
        recent3mBrandUnits={Number(
          insight.metrics?.recent_3m_brand_units ?? 0
        )}
        chain={insight.entities?.chain}
        dc={insight.entities?.dc}
        drilldown={insight.drilldown}
        theme={theme}
      />
    )
  }


  if (insight.type === "order_cadence_risk") {
    return (
      <OrderCadenceRisk
        key={`${insight.type}-${index}`}
        affectedStores={Number(
          insight.metrics?.affected_stores ?? 0
        )}
        avgMonthlyUnits4m={Number(
          insight.metrics?.avg_monthly_units_4m ?? 0
        )}
        avgReplenishedMonths={Number(
          insight.metrics?.avg_replenished_months ?? 0
        )}
        singleSkuStoreCount={Number(
          insight.metrics?.single_sku_store_count ?? 0
        )}
        drilldown={insight.drilldown}
        theme={theme}
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

  const [trialRequested, setTrialRequested] =
    useState(false)

  const [trialRequestLoading, setTrialRequestLoading] =
    useState(false)

  const [trialRequestError, setTrialRequestError] =
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


  async function handleTrialRequest() {
    if (!org?.id || trialRequestLoading) return

    setTrialRequestLoading(true)
    setTrialRequestError(null)

    const { error: requestError } = await supabase
      .from("full_trial_requests")
      .insert({
        org_id: org.id,
      })

    if (requestError) {
      console.error(
        "FULL TRIAL REQUEST ERROR:",
        requestError
      )

      setTrialRequestError(
        "Something went wrong sending your request. Please try again."
      )

      setTrialRequestLoading(false)
      return
    }

    setTrialRequested(true)
    setTrialRequestLoading(false)
  }


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
    return <LoadingScreen mode="results" />
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
          <div
            className="mx-auto mb-5 h-1 w-10 rounded-full"
            style={{ backgroundColor: theme.coral }}
          />

          <p
            className="mb-3 text-[12px] font-semibold uppercase tracking-[0.16em]"
            style={{ color: theme.coralDark }}
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


        {/* FULL ACCESS TRIAL CTA */}

        <section className="mt-14">
          <div
            className="relative overflow-hidden rounded-[32px] border px-7 py-10 text-center md:px-12 md:py-12"
            style={{
              backgroundColor: theme.coralSoft,
              borderColor: "#F3C8BB",
            }}
          >
            <div
              className="absolute left-1/2 top-0 h-1 w-24 -translate-x-1/2 rounded-b-full"
              style={{ backgroundColor: theme.coral }}
            />

            {trialRequested ? (
              <>
                <div
                  className="mx-auto flex h-12 w-12 items-center justify-center rounded-full"
                  style={{
                    backgroundColor: "#FFFFFF",
                    color: theme.coralDark,
                  }}
                >
                  <Check size={22} strokeWidth={2.5} />
                </div>

                <p
                  className="mt-5 text-[12px] font-semibold uppercase tracking-[0.16em]"
                  style={{ color: theme.coralDark }}
                >
                  Request received
                </p>

                <h2
                  className="mx-auto mt-3 max-w-2xl text-[28px] font-semibold leading-tight tracking-[-0.03em] md:text-[32px]"
                  style={{ color: theme.charcoal }}
                >
                  You&apos;re all set!
                </h2>

                <p
                  className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed"
                  style={{ color: theme.brown }}
                >
                  Your request has been received. A member of the SKUba
                  team will reach out within 24 hours to activate your
                  2-month free trial.
                </p>
              </>
            ) : (
              <>
                <p
                  className="text-[12px] font-semibold uppercase tracking-[0.16em]"
                  style={{ color: theme.coralDark }}
                >
                  Try the full SKUba experience
                </p>

                <h2
                  className="mx-auto mt-3 max-w-2xl text-[28px] font-semibold leading-tight tracking-[-0.03em] md:text-[32px]"
                  style={{ color: theme.charcoal }}
                >
                  Get 2 months of full access, free.
                </h2>

                <p
                  className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed"
                  style={{ color: theme.brown }}
                >
                  See what SKUba is like when it&apos;s monitoring your business
                  continuously — with the full product free for your first two months.
                </p>

                <button
                  type="button"
                  disabled={trialRequestLoading}
                  className="mt-7 rounded-full px-7 py-3.5 text-[14px] font-semibold transition-all hover:-translate-y-0.5 hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
                  style={{
                    backgroundColor: theme.coral,
                    color: "#FFFFFF",
                    boxShadow: "0 5px 0 #D9532F",
                  }}
                  onClick={handleTrialRequest}
                >
                  {trialRequestLoading
                    ? "Sending request..."
                    : "Start my 2-month free trial"}
                </button>

                {trialRequestError && (
                  <p
                    className="mx-auto mt-4 max-w-md text-[13px] font-medium"
                    style={{ color: theme.coralDark }}
                  >
                    {trialRequestError}
                  </p>
                )}

                <p
                  className="mt-4 text-[12px]"
                  style={{ color: "#9A766C" }}
                >
                  Full access for 2 months. No commitment.
                </p>
              </>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}