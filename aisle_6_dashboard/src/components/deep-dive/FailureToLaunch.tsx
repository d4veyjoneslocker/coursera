"use client"

import { useOrg } from "@/components/OrgContext"
import InsightDescription from "./InsightDescription"
import { insightDefinitions } from "./insightDefinitions"

type Theme = {
  surface: string
  line: string
  brown: string
  charcoal: string
}

type SkuBreakdownItem = {
  sku?: string
  launched_stores?: number
  at_risk_stores?: number
  reordered_stores?: number
  at_risk_rate?: number
  reorder_rate?: number
  avg_initial_units?: number | null
  avg_initial_units_at_risk?: number | null
  avg_initial_units_reordered?: number | null
  avg_initial_units_gap?: number | null
}

type FailureToLaunchProps = {
  chain: string
  launchMonth: string

  launchedStores: number
  launchedSkus: number
  launchedPlacements: number

  atRiskPlacements: number
  reorderedPlacements: number

  atRiskRate: number
  reorderRate: number

  avgInitialUnitsAtRisk?: number | null
  avgInitialUnitsReordered?: number | null
  avgInitialUnitsGap?: number | null

  skuBreakdown?: SkuBreakdownItem[]

  drilldown?: {
    label: string
    href: string
  }

  theme: Theme
}

function formatMonth(value: string) {
  if (!value) return ""

  const date = new Date(`${value}-01T00:00:00`)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "numeric",
  }).format(date)
}

export default function FailureToLaunch({
  chain,
  launchMonth,
  launchedStores,
  launchedSkus,
  launchedPlacements,
  atRiskPlacements,
  reorderedPlacements,
  atRiskRate,
  reorderRate,
  avgInitialUnitsAtRisk,
  avgInitialUnitsReordered,
  avgInitialUnitsGap,
  skuBreakdown = [],
  drilldown,
  theme,
}: FailureToLaunchProps) {
  const { org } = useOrg()

  const brandColor = org?.primary_color ?? theme.brown

  const reorderedPct = Number(reorderRate ?? 0) * 100
  const atRiskPct = Number(atRiskRate ?? 0) * 100

  const topSku = skuBreakdown?.[0]

  const hasLoadInComparison =
    avgInitialUnitsAtRisk != null &&
    avgInitialUnitsReordered != null

  const hasTopSku =
    Boolean(topSku?.sku) &&
    topSku?.at_risk_stores != null &&
    topSku?.launched_stores != null

  const topSkuAtRiskPct =
    hasTopSku && Number(topSku?.launched_stores) > 0
      ? (
          Number(topSku?.at_risk_stores) /
          Number(topSku?.launched_stores)
        ) * 100
      : 0

  return (
    <div
      className="rounded-[16px] border px-6 py-6"
      style={{
        backgroundColor: theme.surface,
        borderColor: theme.line,
      }}
    >
      {/* HEADER */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <p
            className="text-[13px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: theme.brown }}
          >
            Launch Monitoring
          </p>

          <span style={{ color: theme.line }}>·</span>

          <span
            className="text-[14px] font-semibold uppercase tracking-[0.04em]"
            style={{ color: theme.charcoal }}
          >
            {chain}
          </span>

          <span style={{ color: theme.line }}>·</span>

          <span
            className="text-[14px] font-semibold uppercase tracking-[0.04em]"
            style={{ color: theme.charcoal }}
          >
            {formatMonth(launchMonth)}
          </span>
        </div>

        <InsightDescription
          definition={
            insightDefinitions.failure_to_launch_new_store_risk
          }
        />
      </div>

      {/* LAUNCH OUTCOME */}
      <div
        className="mt-7 rounded-[18px] border px-6 py-6"
        style={{
          borderColor: theme.line,
          backgroundColor: `${theme.charcoal}03`,
        }}
      >
        <p
          className="text-[11px] font-medium uppercase tracking-[0.16em]"
          style={{ color: theme.brown }}
        >
          Launch Outcome
        </p>

        <p
          className="mt-3 text-[14px]"
          style={{ color: theme.brown }}
        >
          <strong style={{ color: theme.charcoal }}>
            {launchedPlacements} placements
          </strong>{" "}
          launched across{" "}
          <strong style={{ color: theme.charcoal }}>
            {launchedStores} stores
          </strong>{" "}
          and{" "}
          <strong style={{ color: theme.charcoal }}>
            {launchedSkus} SKUs
          </strong>
          .
        </p>

        {/* OUTCOME NUMBERS */}
        <div className="mt-7 grid grid-cols-2 gap-8">
          {/* REORDERED */}
          <div>
            <p
              className="text-[42px] font-semibold leading-none tracking-[-0.05em]"
              style={{ color: theme.charcoal }}
            >
              {reorderedPlacements}
            </p>

            <p
              className="mt-2 text-[11px] font-medium uppercase tracking-[0.14em]"
              style={{ color: theme.brown }}
            >
              Reordered
            </p>

            <p
              className="mt-1 text-[13px]"
              style={{ color: theme.brown }}
            >
              {reorderedPct.toFixed(0)}% of placements
            </p>
          </div>

          {/* NEED FOLLOW-UP */}
          <div>
            <p
              className="text-[42px] font-semibold leading-none tracking-[-0.05em]"
              style={{ color: brandColor }}
            >
              {atRiskPlacements}
            </p>

            <p
              className="mt-2 text-[11px] font-medium uppercase tracking-[0.14em]"
              style={{ color: theme.brown }}
            >
              Need Follow-Up
            </p>

            <p
              className="mt-1 text-[13px]"
              style={{ color: theme.brown }}
            >
              {atRiskPct.toFixed(0)}% of placements
            </p>
          </div>
        </div>

        {/* SEGMENTED OUTCOME BAR */}
        <div
          className="mt-7 flex h-4 w-full overflow-hidden rounded-full"
          style={{ backgroundColor: theme.line }}
        >
          <div
            className="h-full"
            style={{
              width: `${Math.min(
                Math.max(reorderedPct, 0),
                100
              )}%`,
              backgroundColor: `${brandColor}55`,
            }}
          />

          <div
            className="h-full"
            style={{
              width: `${Math.min(
                Math.max(atRiskPct, 0),
                100
              )}%`,
              backgroundColor: brandColor,
            }}
          />
        </div>

        <div className="mt-3 flex items-center justify-between gap-4">
          <span
            className="text-[11px]"
            style={{ color: theme.brown }}
          >
            {reorderedPlacements} reordered
          </span>

          <span
            className="text-[11px] font-medium"
            style={{ color: brandColor }}
          >
            {atRiskPlacements} need follow-up
          </span>
        </div>

        <p
          className="mt-5 text-[12px] leading-5"
          style={{
            color: theme.brown,
            opacity: 0.8,
          }}
        >
          Placements needing follow-up received an initial
          shipment but have not reordered after two full
          reorder opportunities.
        </p>
      </div>

      {/* WHAT'S BEHIND IT */}
      {(hasLoadInComparison || hasTopSku) && (
        <div
          className="mt-4 rounded-[18px] border px-6 py-6"
          style={{
            borderColor: theme.line,
            backgroundColor: `${theme.charcoal}03`,
          }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            What&apos;s Behind It
          </p>

          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* INITIAL LOAD-IN */}
            {hasLoadInComparison && (
              <div
                className="rounded-[16px] border px-5 py-5"
                style={{
                  borderColor: theme.line,
                  backgroundColor: theme.surface,
                }}
              >
                <p
                  className="text-[13px] font-medium"
                  style={{ color: theme.charcoal }}
                >
                  Initial load-in
                </p>

                <div className="mt-5 flex items-end gap-8">
                  {/* AT RISK */}
                  <div>
                    <p
                      className="text-[10px] uppercase tracking-[0.12em]"
                      style={{ color: theme.brown }}
                    >
                      At-risk placements
                    </p>

                    <p
                      className="mt-1 text-[30px] font-semibold tracking-[-0.04em]"
                      style={{ color: brandColor }}
                    >
                      {Number(
                        avgInitialUnitsAtRisk
                      ).toFixed(1)}
                    </p>

                    <p
                      className="mt-1 text-[11px]"
                      style={{ color: theme.brown }}
                    >
                      avg units
                    </p>
                  </div>

                  {/* REORDERED */}
                  <div>
                    <p
                      className="text-[10px] uppercase tracking-[0.12em]"
                      style={{ color: theme.brown }}
                    >
                      Reordered placements
                    </p>

                    <p
                      className="mt-1 text-[30px] font-semibold tracking-[-0.04em]"
                      style={{ color: theme.charcoal }}
                    >
                      {Number(
                        avgInitialUnitsReordered
                      ).toFixed(1)}
                    </p>

                    <p
                      className="mt-1 text-[11px]"
                      style={{ color: theme.brown }}
                    >
                      avg units
                    </p>
                  </div>
                </div>

                {avgInitialUnitsGap != null && (
                  <p
                    className="mt-5 text-[13px] leading-6"
                    style={{ color: theme.brown }}
                  >
                    At-risk placements started with{" "}
                    <strong
                      style={{ color: theme.charcoal }}
                    >
                      {Math.abs(
                        Number(avgInitialUnitsGap)
                      ).toFixed(1)}{" "}
                      {Number(avgInitialUnitsGap) < 0
                        ? "fewer"
                        : "more"}{" "}
                      units
                    </strong>{" "}
                    on average.
                  </p>
                )}
              </div>
            )}

            {/* BIGGEST SKU WATCHOUT */}
            {hasTopSku && (
              <div
                className="rounded-[16px] border px-5 py-5"
                style={{
                  borderColor: theme.line,
                  backgroundColor: theme.surface,
                }}
              >
                <p
                  className="text-[13px] font-medium"
                  style={{ color: theme.charcoal }}
                >
                  Biggest SKU watchout
                </p>

                <p
                  className="mt-5 text-[24px] font-semibold uppercase tracking-[-0.03em]"
                  style={{ color: brandColor }}
                >
                  {topSku?.sku}
                </p>

                <p
                  className="mt-2 text-[14px] leading-6"
                  style={{ color: theme.brown }}
                >
                  <strong
                    style={{ color: theme.charcoal }}
                  >
                    {topSku?.at_risk_stores} of{" "}
                    {topSku?.launched_stores} stores
                  </strong>{" "}
                  have not reordered.
                </p>

                <p
                  className="mt-2 text-[13px] font-medium"
                  style={{ color: brandColor }}
                >
                  {topSkuAtRiskPct.toFixed(0)}% need follow-up
                </p>

                {topSku?.avg_initial_units_at_risk != null &&
                  topSku?.avg_initial_units_reordered != null && (
                    <p
                      className="mt-4 text-[12px] leading-5"
                      style={{ color: theme.brown }}
                    >
                      At-risk stores loaded in with{" "}
                      {Number(
                        topSku.avg_initial_units_at_risk
                      ).toFixed(1)}{" "}
                      units on average vs{" "}
                      {Number(
                        topSku.avg_initial_units_reordered
                      ).toFixed(1)}{" "}
                      for stores that reordered.
                    </p>
                  )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* CTA */}
      {drilldown && (
        <div className="mt-5">
          <a
            href={drilldown.href}
            className="inline-flex rounded-full border px-4 py-2 text-sm font-medium transition-opacity hover:opacity-80"
            style={{
              borderColor: theme.line,
              backgroundColor: theme.surface,
              color: theme.charcoal,
            }}
          >
            {drilldown.label} →
          </a>
        </div>
      )}
    </div>
  )
}