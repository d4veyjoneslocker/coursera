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

type OrderCadenceRiskProps = {
  affectedStores: number
  avgMonthlyUnits4m: number
  avgReplenishedMonths: number
  singleSkuStoreCount: number

  drilldown?: {
    label: string
    href: string
  }

  theme: Theme
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(Number(value ?? 0))
}

export default function OrderCadenceRisk({
  affectedStores,
  avgMonthlyUnits4m,
  avgReplenishedMonths,
  singleSkuStoreCount,
  drilldown,
  theme,
}: OrderCadenceRiskProps) {
  const { org } = useOrg()

  const brandColor =
    org?.primary_color ?? theme.brown

  const cadencePct = Math.min(
    Math.max(
      (Number(avgReplenishedMonths ?? 0) / 4) * 100,
      0
    ),
    100
  )

  const singleSkuShare =
    affectedStores > 0
      ? (singleSkuStoreCount / affectedStores) * 100
      : 0

  // Only show this when it is actually material.
  const hasMeaningfulSingleSkuExposure =
    singleSkuStoreCount >= 3 &&
    singleSkuShare >= 10

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
        <p
          className="text-[13px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: theme.brown }}
        >
          Missed Replenishment
        </p>

        <InsightDescription
          definition={insightDefinitions.order_cadence_risk}
        />
      </div>

      {/* ================================================= */}
      {/* PRIMARY STORY */}
      {/* ================================================= */}

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[1fr_0.9fr]">
        {/* LEFT */}

        <div>
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Expected Replenishments Missed
          </p>

          <div className="mt-3 flex items-end gap-3">
            <p
              className="text-[54px] font-semibold leading-none tracking-[-0.06em]"
              style={{ color: brandColor }}
            >
              {formatNumber(affectedStores)}
            </p>

            <p
              className="pb-1.5 text-[15px]"
              style={{ color: theme.brown }}
            >
              stores
            </p>
          </div>

          <p
            className="mt-5 max-w-lg text-[16px] leading-7"
            style={{ color: theme.charcoal }}
          >
            {formatNumber(affectedStores)} stores that had been
            ordering consistently did not receive their expected
            recent replenishment.
          </p>

          <p
            className="mt-4 text-[13px] leading-6"
            style={{ color: theme.brown }}
          >
            These were not occasional buyers — they purchased in an
            average of{" "}
            <strong style={{ color: theme.charcoal }}>
              {Number(avgReplenishedMonths ?? 0).toFixed(1)}
              {" "}of the prior 4 months
            </strong>
            .
          </p>
        </div>

        {/* RIGHT */}

        <div
          className="rounded-[18px] border px-5 py-5"
          style={{
            backgroundColor: "#FCFAF6",
            borderColor: theme.line,
          }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Why This Stands Out
          </p>

          <div className="mt-5">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p
                  className="text-[30px] font-semibold tracking-[-0.05em]"
                  style={{ color: theme.charcoal }}
                >
                  {Number(avgReplenishedMonths ?? 0).toFixed(1)}
                  <span
                    className="ml-1 text-[15px] font-normal"
                    style={{ color: theme.brown }}
                  >
                    / 4 months
                  </span>
                </p>

                <p
                  className="mt-1 text-[12px]"
                  style={{ color: theme.brown }}
                >
                  typical prior purchase frequency
                </p>
              </div>

              <p
                className="text-[12px] font-medium"
                style={{ color: brandColor }}
              >
                {cadencePct.toFixed(0)}% cadence
              </p>
            </div>

            <div
              className="mt-4 h-2.5 overflow-hidden rounded-full"
              style={{ backgroundColor: theme.line }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${cadencePct}%`,
                  backgroundColor: brandColor,
                }}
              />
            </div>
          </div>

          <div
            className="mt-6 border-t pt-5"
            style={{ borderColor: theme.line }}
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p
                  className="text-[11px] uppercase tracking-[0.12em]"
                  style={{ color: theme.brown }}
                >
                  Latest Expected Replenishment
                </p>

                <p
                  className="mt-1 text-[13px]"
                  style={{ color: theme.charcoal }}
                >
                  None of these stores replenished.
                </p>
              </div>

              <p
                className="text-[30px] font-semibold tracking-[-0.05em]"
                style={{ color: brandColor }}
              >
                0
              </p>
            </div>
          </div>

          <p
            className="mt-5 text-[12px] leading-5"
            style={{ color: theme.brown }}
          >
            The contrast between their normal ordering cadence and
            the latest period is what triggered this finding.
          </p>
        </div>
      </div>

      {/* ================================================= */}
      {/* VOLUME EXPOSURE */}
      {/* ================================================= */}

      <div
        className="mt-8 border-t pt-7"
        style={{ borderColor: theme.line }}
      >
        <p
          className="text-[11px] font-medium uppercase tracking-[0.16em]"
          style={{ color: theme.brown }}
        >
          What The Miss Represents
        </p>

        <div className="mt-5 grid grid-cols-1 gap-7 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
          <div>
            <div className="flex items-end gap-3">
              <p
                className="text-[42px] font-semibold leading-none tracking-[-0.05em]"
                style={{ color: brandColor }}
              >
                {formatNumber(avgMonthlyUnits4m)}
              </p>

              <p
                className="pb-1 text-[13px]"
                style={{ color: theme.brown }}
              >
                units / month
              </p>
            </div>

            <p
              className="mt-2 text-[12px]"
              style={{ color: theme.brown }}
            >
              normal combined monthly volume from these stores
            </p>
          </div>

          <div
            className="border-l-[3px] pl-5"
            style={{ borderColor: brandColor }}
          >
            <p
              className="text-[15px] leading-7"
              style={{ color: theme.charcoal }}
            >
              Before this missed replenishment, these stores
              collectively represented about{" "}
              <strong>
                {formatNumber(avgMonthlyUnits4m)} units in a
                typical month
              </strong>
              . That gives a sense of the volume tied to the
              ordering pattern that has now gone quiet.
            </p>
          </div>
        </div>
      </div>

      {/* ================================================= */}
      {/* SINGLE-SKU EXPOSURE */}
      {/* ================================================= */}

      {hasMeaningfulSingleSkuExposure && (
        <div
          className="mt-8 border-t pt-7"
          style={{ borderColor: theme.line }}
        >
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div>
              <p
                className="text-[11px] font-medium uppercase tracking-[0.16em]"
                style={{ color: theme.brown }}
              >
                Single-SKU Exposure
              </p>

              <p
                className="mt-2 max-w-2xl text-[13px] leading-6"
                style={{ color: theme.charcoal }}
              >
                {formatNumber(singleSkuStoreCount)} of the affected
                stores only carry one of your SKUs. In those stores,
                a missed replenishment means the entire brand has
                stopped shipping.
              </p>
            </div>

            <div className="text-right">
              <p
                className="text-[28px] font-semibold tracking-[-0.04em]"
                style={{ color: brandColor }}
              >
                {singleSkuShare.toFixed(0)}%
              </p>

              <p
                className="mt-1 text-[11px]"
                style={{ color: theme.brown }}
              >
                of affected stores
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ================================================= */}
      {/* CTA */}
      {/* ================================================= */}

      {drilldown && (
        <div className="mt-8">
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