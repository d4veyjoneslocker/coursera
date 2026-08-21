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

type ChainStrugglingProps = {
  chain: string

  strugglingStores: number
  totalStores: number
  strugglingPct: number
  overallStrugglingPct: number
  vsAverage: number

  reorderRateCurrent?: number | null
  reorderRatePrior?: number | null
  reorderRateChange?: number | null

  latestOrderStoreCount?: number | null
  latestOrderMonth?: string | null

  rootCauseText?: string | null

  drilldown?: {
    label: string
    href: string
  }

  theme: Theme
}

export default function ChainStruggling({
  chain,
  strugglingStores,
  totalStores,
  strugglingPct,
  overallStrugglingPct,
  vsAverage,

  reorderRateCurrent,
  reorderRatePrior,
  reorderRateChange,

  latestOrderStoreCount,
  latestOrderMonth,

  rootCauseText,

  drilldown,
  theme,
}: ChainStrugglingProps) {
  const { org } = useOrg()

  const brandColor =
    org?.primary_color ?? theme.brown

  const secondaryColor =
    org?.secondary_color ?? brandColor

  const strugglingPercent =
    Number(strugglingPct ?? 0) * 100

  const overallPercent =
    Number(overallStrugglingPct ?? 0) * 100

  const vsAveragePts =
    Number(vsAverage ?? 0) * 100

  const reorderCurrentPct =
    Number(reorderRateCurrent ?? 0) * 100

  const reorderPriorPct =
    Number(reorderRatePrior ?? 0) * 100

  const reorderChangePts =
    Number(reorderRateChange ?? 0) * 100

  const hasReorderData =
    reorderRateCurrent != null &&
    reorderRatePrior != null &&
    reorderRateChange != null

  const hasRecentOrdering =
    latestOrderStoreCount != null &&
    latestOrderStoreCount > 0

  const hasDiagnostics =
    hasReorderData ||
    hasRecentOrdering ||
    Boolean(rootCauseText)

  /*
   * Each square represents an actual store.
   *
   * For very large chains, fall back to a proportional
   * 50-square visualization so the UI stays usable.
   */
  const useActualStores = totalStores <= 50

  const visualTotal = useActualStores
    ? totalStores
    : 50

  const visualStruggling = useActualStores
    ? strugglingStores
    : Math.round(
        Math.min(Math.max(strugglingPct, 0), 1) * visualTotal
      )

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
            Struggling Chain
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
        </div>

        <InsightDescription
          definition={insightDefinitions.chain_struggling}
        />
      </div>

      {/* ================================================= */}
      {/* PRIMARY STORY */}
      {/* ================================================= */}

      <div className="mt-7 grid grid-cols-1 gap-8 lg:grid-cols-[0.9fr_1.1fr]">

        {/* LEFT: MAIN METRIC */}
        <div>
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Stores Struggling
          </p>

          <div className="mt-3 flex items-end gap-3">
            <p
              className="text-[48px] font-semibold leading-none tracking-[-0.05em]"
              style={{ color: brandColor }}
            >
              {strugglingPercent.toFixed(0)}%
            </p>

            <p
              className="pb-1 text-[14px]"
              style={{ color: theme.brown }}
            >
              {strugglingStores} of {totalStores} stores
            </p>
          </div>

          <p
            className="mt-5 max-w-md text-[16px] leading-7"
            style={{ color: theme.charcoal }}
          >
            Struggling stores are more concentrated at{" "}
            <strong>{chain}</strong> than across your business
            overall.
          </p>

          <div className="mt-5 flex items-center gap-3">
            <span
              className="text-[22px] font-semibold tracking-[-0.03em]"
              style={{ color: brandColor }}
            >
              +{vsAveragePts.toFixed(0)} pts
            </span>

            <span
              className="text-[13px]"
              style={{ color: theme.brown }}
            >
              above business average
            </span>
          </div>
        </div>

        {/* RIGHT: STORE VISUAL */}
        <div
          className="rounded-[18px] border px-5 py-5"
          style={{
            borderColor: theme.line,
            backgroundColor: theme.surface,
          }}
        >
          <div className="flex items-center justify-between gap-4">
            <p
              className="text-[11px] font-medium uppercase tracking-[0.16em]"
              style={{ color: theme.brown }}
            >
              Store Health
            </p>

            <p
              className="text-[12px]"
              style={{ color: theme.brown }}
            >
              Business avg{" "}
              <strong style={{ color: theme.charcoal }}>
                {overallPercent.toFixed(0)}%
              </strong>
            </p>
          </div>

          {/* STORE SQUARES */}
          <div className="mt-5 flex flex-wrap gap-2">
            {Array.from({ length: visualTotal }).map(
              (_, index) => {
                const isStruggling =
                  index < visualStruggling

                return (
                  <div
                    key={index}
                    className="h-4 w-4 rounded-[4px] border"
                    style={{
                      backgroundColor: isStruggling
                        ? brandColor
                        : "transparent",

                      borderColor: isStruggling
                        ? brandColor
                        : theme.line,
                    }}
                  />
                )
              }
            )}
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2">
            <div className="flex items-center gap-2">
              <div
                className="h-3 w-3 rounded-[3px]"
                style={{
                  backgroundColor: brandColor,
                }}
              />

              <span
                className="text-[12px]"
                style={{ color: theme.brown }}
              >
                {useActualStores
                  ? `${strugglingStores} struggling`
                  : `${strugglingPercent.toFixed(0)}% struggling`}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div
                className="h-3 w-3 rounded-[3px] border"
                style={{
                  borderColor: theme.line,
                }}
              />

              <span
                className="text-[12px]"
                style={{ color: theme.brown }}
              >
                {useActualStores
                  ? `${totalStores - strugglingStores} healthy`
                  : `${(100 - strugglingPercent).toFixed(0)}% healthy`}
              </span>
            </div>
          </div>

          {!useActualStores && (
            <p
              className="mt-3 text-[10px]"
              style={{ color: theme.brown }}
            >
              Each square represents approximately{" "}
              {(totalStores / visualTotal).toFixed(1)} stores.
            </p>
          )}
        </div>
      </div>

      {/* ================================================= */}
      {/* BENCHMARK */}
      {/* ================================================= */}

      <div
        className="mt-7 border-t pt-6"
        style={{ borderColor: theme.line }}
      >
        <div className="flex items-end justify-between gap-5">
          <div>
            <p
              className="text-[11px] font-medium uppercase tracking-[0.16em]"
              style={{ color: theme.brown }}
            >
              Struggling Store Rate
            </p>

            <p
              className="mt-2 text-[13px]"
              style={{ color: theme.brown }}
            >
              {chain} vs your overall business
            </p>
          </div>

          <div className="flex items-baseline gap-2">
            <span
              className="text-[20px] font-semibold"
              style={{ color: brandColor }}
            >
              {strugglingPercent.toFixed(0)}%
            </span>

            <span
              className="text-[12px]"
              style={{ color: theme.brown }}
            >
              vs
            </span>

            <span
              className="text-[20px] font-semibold"
              style={{ color: theme.charcoal }}
            >
              {overallPercent.toFixed(0)}%
            </span>
          </div>
        </div>

        {/* BENCHMARK TRACK */}
        <div
          className="relative mt-4 h-3 rounded-full"
          style={{
            backgroundColor: theme.line,
          }}
        >
          <div
            className="absolute bottom-0 left-0 top-0 rounded-full"
            style={{
              width: `${Math.min(
                Math.max(strugglingPercent, 0),
                100
              )}%`,
              backgroundColor: brandColor,
            }}
          />

          <div
            className="absolute -bottom-1 -top-1 w-[2px]"
            style={{
              left: `${Math.min(
                Math.max(overallPercent, 0),
                100
              )}%`,
              backgroundColor: secondaryColor,
            }}
          />
        </div>

        <div
          className="relative mt-2 h-5"
          style={{ color: theme.brown }}
        >
          <span
            className="absolute whitespace-nowrap text-[10px]"
            style={{
              left: `${Math.min(
                Math.max(overallPercent, 0),
                100
              )}%`,
              transform: "translateX(-50%)",
            }}
          >
            ↑ avg
          </span>
        </div>
      </div>

      {/* ================================================= */}
      {/* DIAGNOSTICS */}
      {/* ================================================= */}

      {hasDiagnostics && (
        <div
          className="mt-5 border-t pt-6"
          style={{ borderColor: theme.line }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            What&apos;s Behind It
          </p>

          <div className="mt-5 grid grid-cols-1 gap-x-10 gap-y-6 md:grid-cols-2">

            {/* REORDER BEHAVIOR */}
            {hasReorderData && (
              <div>
                <p
                  className="text-[12px] font-medium"
                  style={{ color: theme.charcoal }}
                >
                  Reorder behavior
                </p>

                <div className="mt-3 flex items-center gap-4">
                  <div>
                    <p
                      className="text-[10px] uppercase tracking-[0.12em]"
                      style={{ color: theme.brown }}
                    >
                      6 months ago
                    </p>

                    <p
                      className="mt-1 text-[24px] font-semibold"
                      style={{ color: theme.charcoal }}
                    >
                      {reorderPriorPct.toFixed(0)}%
                    </p>
                  </div>

                  <span
                    className="text-[18px]"
                    style={{ color: secondaryColor }}
                  >
                    →
                  </span>

                  <div>
                    <p
                      className="text-[10px] uppercase tracking-[0.12em]"
                      style={{ color: theme.brown }}
                    >
                      Now
                    </p>

                    <p
                      className="mt-1 text-[24px] font-semibold"
                      style={{ color: theme.charcoal }}
                    >
                      {reorderCurrentPct.toFixed(0)}%
                    </p>
                  </div>
                </div>

                <p
                  className="mt-2 text-[12px]"
                  style={{ color: theme.brown }}
                >
                  {reorderChangePts > 0
                    ? `Reorder rate improved ${reorderChangePts.toFixed(
                        0
                      )} pts.`
                    : reorderChangePts < 0
                    ? `Reorder rate declined ${Math.abs(
                        reorderChangePts
                      ).toFixed(0)} pts.`
                    : "Reorder rate is unchanged."}
                </p>
              </div>
            )}

            {/* RECENT ORDERING */}
            {hasRecentOrdering && (
              <div>
                <p
                  className="text-[12px] font-medium"
                  style={{ color: theme.charcoal }}
                >
                  Recent ordering
                </p>

                <div className="mt-3 flex items-baseline gap-2">
                  <span
                    className="text-[24px] font-semibold"
                    style={{ color: brandColor }}
                  >
                    {latestOrderStoreCount}
                  </span>

                  <span
                    className="text-[13px]"
                    style={{ color: theme.brown }}
                  >
                    struggling stores
                  </span>
                </div>

                <p
                  className="mt-2 text-[12px] leading-5"
                  style={{ color: theme.brown }}
                >
                  Last ordered
                  {latestOrderMonth
                    ? ` in ${latestOrderMonth}.`
                    : " in the most recent ordering month."}
                </p>
              </div>
            )}

            {/* ROOT CAUSE */}
            {rootCauseText && (
              <div
                className="md:col-span-2"
              >
                <div
                  className="border-l-[3px] pl-4"
                  style={{
                    borderColor: brandColor,
                  }}
                >
                  <p
                    className="text-[12px] font-medium"
                    style={{ color: theme.charcoal }}
                  >
                    Concentration signal
                  </p>

                  <p
                    className="mt-2 max-w-3xl text-[13px] leading-6"
                    style={{ color: theme.brown }}
                  >
                    {rootCauseText}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* CTA */}
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