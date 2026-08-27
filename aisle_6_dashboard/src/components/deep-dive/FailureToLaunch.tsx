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
  const { org, skuColors } = useOrg()

  const brandColor =
    org?.primary_color ?? theme.brown

  const atRiskPct =
    Number(atRiskRate ?? 0) * 100

  const reorderedPct =
    Number(reorderRate ?? 0) * 100

  const placementsPerStore =
    launchedStores > 0
      ? launchedPlacements / launchedStores
      : 0

  const hasLoadInComparison =
    avgInitialUnitsAtRisk != null &&
    avgInitialUnitsReordered != null

  const initialUnitsGap =
    hasLoadInComparison
      ? Number(avgInitialUnitsAtRisk) -
        Number(avgInitialUnitsReordered)
      : null

  const lighterLoadInPct =
    hasLoadInComparison &&
    Number(avgInitialUnitsReordered) > 0
      ? ((Number(avgInitialUnitsReordered) -
          Number(avgInitialUnitsAtRisk)) /
          Number(avgInitialUnitsReordered)) *
        100
      : null

  const rankedSkus = [...skuBreakdown]
    .filter(
      (item) =>
        item.sku &&
        item.launched_stores != null &&
        Number(item.launched_stores) > 0
    )
    .sort((a, b) => {
      const aRate =
        Number(a.at_risk_stores ?? 0) /
        Number(a.launched_stores ?? 1)

      const bRate =
        Number(b.at_risk_stores ?? 0) /
        Number(b.launched_stores ?? 1)

      return bRate - aRate
    })

  const topSku = rankedSkus[0]

  const topSkuAtRiskPct =
    topSku &&
    Number(topSku.launched_stores ?? 0) > 0
      ? (Number(topSku.at_risk_stores ?? 0) /
          Number(topSku.launched_stores)) *
        100
      : 0

  const getSkuColor = (sku?: string) => {
    if (!sku) return brandColor

    return (
      skuColors?.[sku] ??
      skuColors?.[sku.trim().toUpperCase()] ??
      brandColor
    )
  }

  return (
    <div
      className="rounded-[16px] border px-6 py-6"
      style={{
        backgroundColor: theme.surface,
        borderColor: theme.line,
      }}
    >
      {/* ================================================= */}
      {/* HEADER */}
      {/* ================================================= */}

      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <p
            className="text-[13px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: theme.brown }}
          >
            Launch Monitoring
          </p>

          <span style={{ color: theme.line }}>
            ·
          </span>

          <span
            className="text-[14px] font-semibold uppercase tracking-[0.04em]"
            style={{ color: theme.charcoal }}
          >
            {chain}
          </span>

          <span style={{ color: theme.line }}>
            ·
          </span>

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

      {/* ================================================= */}
      {/* PRIMARY STORY */}
      {/* ================================================= */}

      <div className="mt-7 grid grid-cols-1 gap-8 lg:grid-cols-[0.88fr_1.12fr]">
        {/* LEFT */}
        <div>
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Launches Not Reordering
          </p>

          <div className="mt-3 flex items-end gap-3">
            <p
              className="text-[52px] font-semibold leading-none tracking-[-0.06em]"
              style={{ color: brandColor }}
            >
              {atRiskPct.toFixed(0)}%
            </p>

            <p
              className="pb-1 text-[14px]"
              style={{ color: theme.brown }}
            >
              of placements
            </p>
          </div>

          <p
            className="mt-5 max-w-md text-[16px] leading-7"
            style={{ color: theme.charcoal }}
          >
            <strong>
              {atRiskPlacements} of{" "}
              {launchedPlacements} placements
            </strong>{" "}
            received an initial shipment but have not
            reordered after two full reorder opportunities.
          </p>

          <div
            className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px]"
            style={{ color: theme.brown }}
          >
            <span>
              <strong
                style={{ color: theme.charcoal }}
              >
                {launchedStores}
              </strong>{" "}
              stores launched
            </span>

            <span>
              <strong
                style={{ color: theme.charcoal }}
              >
                {launchedSkus}
              </strong>{" "}
              SKUs
            </span>
          </div>
        </div>

        {/* RIGHT: OUTCOME */}
        <div
          className="rounded-[18px] border px-5 py-5"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <div className="flex items-start justify-between gap-6">
            <div>
              <p
                className="text-[11px] font-medium uppercase tracking-[0.16em]"
                style={{ color: theme.brown }}
              >
                Launch Outcome
              </p>

              <p
                className="mt-2 text-[13px]"
                style={{ color: theme.brown }}
              >
                {launchedPlacements} placements in the{" "}
                {formatMonth(launchMonth)} cohort
              </p>
            </div>

            <div className="text-right">
              <p
                className="text-[21px] font-semibold"
                style={{ color: theme.charcoal }}
              >
                {reorderedPlacements}
              </p>

              <p
                className="text-[10px] uppercase tracking-[0.12em]"
                style={{ color: theme.brown }}
              >
                reordered
              </p>
            </div>
          </div>

          {/* SPLIT OUTCOME */}
          <div
            className="mt-7 grid gap-1.5"
            style={{
              gridTemplateColumns: `${Math.max(
                reorderedPct,
                1
              )}fr ${Math.max(atRiskPct, 1)}fr`,
            }}
          >
            <div
              className="flex h-20 items-end rounded-l-[14px] px-4 py-3"
              style={{
                backgroundColor: "#E4E0DA",
              }}
            >
              <div>
                <p
                  className="text-[22px] font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  {reorderedPct.toFixed(0)}%
                </p>

                <p
                  className="mt-1 text-[11px]"
                  style={{ color: theme.brown }}
                >
                  Reordered
                </p>
              </div>
            </div>

            <div
              className="flex h-20 items-end rounded-r-[14px] px-4 py-3"
              style={{
                backgroundColor: brandColor,
              }}
            >
              <div>
                <p className="text-[22px] font-semibold text-white">
                  {atRiskPct.toFixed(0)}%
                </p>

                <p className="mt-1 text-[11px] text-white/80">
                  Need follow-up
                </p>
              </div>
            </div>
          </div>

          <p
            className="mt-5 text-[12px] leading-5"
            style={{ color: theme.brown }}
          >
            A placement is flagged after it has had two
            full opportunities to reorder and still has no
            repeat order.
          </p>
        </div>
      </div>

      {/* ================================================= */}
      {/* LOAD-IN EVIDENCE */}
      {/* ================================================= */}

      {hasLoadInComparison && (
        <div
          className="mt-7 border-t pt-6"
          style={{ borderColor: theme.line }}
        >
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_300px]">
            {/* LEFT */}
            <div>
              <div className="flex flex-wrap items-end justify-between gap-5">
                <div>
                  <p
                    className="text-[11px] font-medium uppercase tracking-[0.16em]"
                    style={{ color: theme.brown }}
                  >
                    Initial Load-In
                  </p>

                  <p
                    className="mt-2 text-[13px]"
                    style={{ color: theme.brown }}
                  >
                    At-risk placements started with less
                    inventory
                  </p>
                </div>

                {lighterLoadInPct != null && (
                  <div className="text-right">
                    <span
                      className="text-[24px] font-semibold"
                      style={{ color: brandColor }}
                    >
                      {lighterLoadInPct > 0
                        ? `${lighterLoadInPct.toFixed(
                            0
                          )}% lighter`
                        : `${Math.abs(
                            lighterLoadInPct
                          ).toFixed(0)}% heavier`}
                    </span>

                    <p
                      className="mt-1 text-[11px]"
                      style={{ color: theme.brown }}
                    >
                      initial shipment
                    </p>
                  </div>
                )}
              </div>

              {/* PAIRED NUMBERS */}
              <div className="mt-6 grid grid-cols-2 gap-4">
                <div
                  className="border-l-[3px] pl-4"
                  style={{
                    borderColor: "#D5D0C9",
                  }}
                >
                  <p
                    className="text-[10px] font-medium uppercase tracking-[0.13em]"
                    style={{ color: theme.brown }}
                  >
                    Reordered
                  </p>

                  <div className="mt-2 flex items-baseline gap-2">
                    <span
                      className="text-[34px] font-semibold tracking-[-0.045em]"
                      style={{
                        color: theme.charcoal,
                      }}
                    >
                      {Number(
                        avgInitialUnitsReordered
                      ).toFixed(1)}
                    </span>

                    <span
                      className="text-[11px]"
                      style={{ color: theme.brown }}
                    >
                      avg units
                    </span>
                  </div>
                </div>

                <div
                  className="border-l-[3px] pl-4"
                  style={{
                    borderColor: brandColor,
                  }}
                >
                  <p
                    className="text-[10px] font-medium uppercase tracking-[0.13em]"
                    style={{ color: theme.brown }}
                  >
                    Need follow-up
                  </p>

                  <div className="mt-2 flex items-baseline gap-2">
                    <span
                      className="text-[34px] font-semibold tracking-[-0.045em]"
                      style={{ color: brandColor }}
                    >
                      {Number(
                        avgInitialUnitsAtRisk
                      ).toFixed(1)}
                    </span>

                    <span
                      className="text-[11px]"
                      style={{ color: theme.brown }}
                    >
                      avg units
                    </span>
                  </div>
                </div>
              </div>

              {initialUnitsGap != null && (
                <div
                  className="mt-6 max-w-2xl border-l pl-4"
                  style={{
                    borderColor: theme.line,
                  }}
                >
                  <p
                    className="text-[12px] leading-6"
                    style={{ color: theme.brown }}
                  >
                    At-risk placements received{" "}
                    <strong
                      style={{
                        color: theme.charcoal,
                      }}
                    >
                      {Math.abs(
                        initialUnitsGap
                      ).toFixed(1)}{" "}
                      {initialUnitsGap < 0
                        ? "fewer"
                        : "more"}{" "}
                      units
                    </strong>{" "}
                    on their initial shipment. This is a
                    correlation, not necessarily the cause
                    of the missed reorder.
                  </p>
                </div>
              )}
            </div>

            {/* COHORT CONTEXT */}
            <div
              className="rounded-[16px] border px-5 py-5"
              style={{
                backgroundColor: "#FCFAF6",
                borderColor: theme.line,
              }}
            >
              <p
                className="text-[10px] font-medium uppercase tracking-[0.16em]"
                style={{ color: theme.brown }}
              >
                Cohort At A Glance
              </p>

              <div className="mt-5 grid grid-cols-2 gap-x-5 gap-y-5">
                <div>
                  <p
                    className="text-[24px] font-semibold tracking-[-0.04em]"
                    style={{
                      color: theme.charcoal,
                    }}
                  >
                    {launchedStores}
                  </p>

                  <p
                    className="mt-1 text-[11px]"
                    style={{ color: theme.brown }}
                  >
                    stores
                  </p>
                </div>

                <div>
                  <p
                    className="text-[24px] font-semibold tracking-[-0.04em]"
                    style={{
                      color: theme.charcoal,
                    }}
                  >
                    {launchedSkus}
                  </p>

                  <p
                    className="mt-1 text-[11px]"
                    style={{ color: theme.brown }}
                  >
                    SKUs
                  </p>
                </div>

                <div>
                  <p
                    className="text-[24px] font-semibold tracking-[-0.04em]"
                    style={{
                      color: theme.charcoal,
                    }}
                  >
                    {launchedPlacements}
                  </p>

                  <p
                    className="mt-1 text-[11px]"
                    style={{ color: theme.brown }}
                  >
                    placements
                  </p>
                </div>

                <div>
                  <p
                    className="text-[24px] font-semibold tracking-[-0.04em]"
                    style={{
                      color: theme.charcoal,
                    }}
                  >
                    {placementsPerStore.toFixed(1)}
                  </p>

                  <p
                    className="mt-1 text-[11px]"
                    style={{ color: theme.brown }}
                  >
                    per store
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================================================= */}
      {/* SKU CONCENTRATION */}
      {/* ================================================= */}

      {topSku && (
        <div
          className="mt-7 border-t pt-6"
          style={{ borderColor: theme.line }}
        >
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <p
                className="text-[11px] font-medium uppercase tracking-[0.16em]"
                style={{ color: theme.brown }}
              >
                Where The Risk Is Concentrated
              </p>

              <p
                className="mt-2 text-[13px]"
                style={{ color: theme.brown }}
              >
                {topSku.sku} is the clearest SKU
                watchout in this cohort
              </p>
            </div>

            <div className="text-right">
              <span
                className="text-[24px] font-semibold"
                style={{
                  color: getSkuColor(topSku.sku),
                }}
              >
                {topSkuAtRiskPct.toFixed(0)}%
              </span>

              <p
                className="mt-1 text-[11px]"
                style={{ color: theme.brown }}
              >
                of {topSku.sku} stores need follow-up
              </p>
            </div>
          </div>

          {/* RANKED SKU ROWS */}
          <div className="mt-6 divide-y" style={{ borderColor: theme.line }}>
            {rankedSkus.map((item, index) => {
              const launched =
                Number(item.launched_stores ?? 0)

              const atRisk =
                Number(item.at_risk_stores ?? 0)

              const reordered =
                item.reordered_stores != null
                  ? Number(item.reordered_stores)
                  : Math.max(launched - atRisk, 0)

              const rate =
                launched > 0
                  ? (atRisk / launched) * 100
                  : 0

              const skuColor =
                getSkuColor(item.sku)

              return (
                <div
                  key={`${item.sku}-${index}`}
                  className="grid grid-cols-[1fr_auto_auto] items-center gap-5 py-4"
                  style={{
                    borderColor: theme.line,
                  }}
                >
                  <div>
                    <p
                      className={`text-[14px] uppercase tracking-[-0.01em] ${
                        index === 0
                          ? "font-semibold"
                          : "font-medium"
                      }`}
                      style={{
                        color:
                          index === 0
                            ? skuColor
                            : theme.charcoal,
                      }}
                    >
                      {item.sku}
                    </p>

                    <p
                      className="mt-1 text-[11px]"
                      style={{ color: theme.brown }}
                    >
                      {atRisk} of {launched} launched
                      stores
                    </p>
                  </div>

                  <div className="text-right">
                    <p
                      className="text-[13px] font-semibold"
                      style={{
                        color: theme.charcoal,
                      }}
                    >
                      {atRisk} at risk
                    </p>

                    <p
                      className="mt-1 text-[10px]"
                      style={{ color: theme.brown }}
                    >
                      {reordered} reordered
                    </p>
                  </div>

                  <div
                    className="w-[54px] rounded-full px-2.5 py-1.5 text-center text-[12px] font-semibold"
                    style={{
                      backgroundColor:
                        index === 0
                          ? `${skuColor}18`
                          : "#F3F0EB",
                      color:
                        index === 0
                          ? skuColor
                          : theme.brown,
                    }}
                  >
                    {rate.toFixed(0)}%
                  </div>
                </div>
              )
            })}
          </div>

          {topSku.avg_initial_units_at_risk != null &&
            topSku.avg_initial_units_reordered != null && (
              <p
                className="mt-5 text-[12px] leading-5"
                style={{ color: theme.brown }}
              >
                {topSku.sku} is the highest-risk SKU
                shown. Its at-risk stores loaded in with{" "}
                <strong
                  style={{ color: theme.charcoal }}
                >
                  {Number(
                    topSku.avg_initial_units_at_risk
                  ).toFixed(1)}
                </strong>{" "}
                units on average vs{" "}
                <strong
                  style={{ color: theme.charcoal }}
                >
                  {Number(
                    topSku.avg_initial_units_reordered
                  ).toFixed(1)}
                </strong>{" "}
                for stores that reordered.
              </p>
            )}
        </div>
      )}

      {/* ================================================= */}
      {/* CTA */}
      {/* ================================================= */}

      {drilldown && (
        <div className="mt-7">
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