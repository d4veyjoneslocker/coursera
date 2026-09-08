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

  const cadencePct =
    Math.min(
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

  const hasSingleSkuExposure =
    singleSkuStoreCount > 0

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
            Missed Replenishment
          </p>
        </div>

        <InsightDescription
          definition={insightDefinitions.order_cadence_risk}
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
            Stores Off Cadence
          </p>

          <div className="mt-3 flex items-end gap-3">
            <p
              className="text-[52px] font-semibold leading-none tracking-[-0.06em]"
              style={{ color: brandColor }}
            >
              {affectedStores}
            </p>

            <p
              className="pb-1 text-[14px]"
              style={{ color: theme.brown }}
            >
              stores
            </p>
          </div>

          <p
            className="mt-5 max-w-md text-[16px] leading-7"
            style={{ color: theme.charcoal }}
          >
            These stores had been replenishing consistently,
            but have now missed their expected recent order.
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px]">
            <span style={{ color: theme.brown }}>
              Averaged{" "}
              <strong style={{ color: theme.charcoal }}>
                {Number(avgReplenishedMonths ?? 0).toFixed(1)}
              </strong>{" "}
              of 4 prior months
            </span>
          </div>
        </div>

        {/* RIGHT: CADENCE VISUAL */}
        <div
          className="rounded-[18px] border px-5 py-5"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <div className="flex items-start justify-between gap-5">
            <div>
              <p
                className="text-[11px] font-medium uppercase tracking-[0.16em]"
                style={{ color: theme.brown }}
              >
                Replenishment History
              </p>

              <p
                className="mt-2 text-[13px]"
                style={{ color: theme.brown }}
              >
                Average purchase frequency before the interruption
              </p>
            </div>

            <div className="text-right">
              <p
                className="text-[21px] font-semibold"
                style={{ color: brandColor }}
              >
                {Number(avgReplenishedMonths ?? 0).toFixed(1)}
              </p>

              <p
                className="text-[10px] uppercase tracking-[0.12em]"
                style={{ color: theme.brown }}
              >
                of 4 months
              </p>
            </div>
          </div>

          <div className="mt-7 grid grid-cols-5 gap-2">
            {Array.from({ length: 4 }).map(
              (_, index) => {
                const monthFilled =
                  index < Math.round(avgReplenishedMonths)

                return (
                  <div key={index}>
                    <div
                      className="flex h-16 items-end rounded-[10px] border px-2 py-2"
                      style={{
                        backgroundColor: monthFilled
                          ? brandColor
                          : "transparent",
                        borderColor: monthFilled
                          ? brandColor
                          : theme.line,
                      }}
                    >
                      <span
                        className="text-[10px] font-medium"
                        style={{
                          color: monthFilled
                            ? "white"
                            : theme.brown,
                        }}
                      >
                        {monthFilled ? "Ordered" : "No order"}
                      </span>
                    </div>

                    <p
                      className="mt-2 text-center text-[9px] uppercase tracking-[0.1em]"
                      style={{ color: theme.brown }}
                    >
                      Prior {4 - index}
                    </p>
                  </div>
                )
              }
            )}

            <div>
              <div
                className="flex h-16 items-end rounded-[10px] border px-2 py-2"
                style={{
                  borderColor: brandColor,
                  backgroundColor: `${brandColor}12`,
                }}
              >
                <span
                  className="text-[10px] font-semibold"
                  style={{ color: brandColor }}
                >
                  Missed
                </span>
              </div>

              <p
                className="mt-2 text-center text-[9px] uppercase tracking-[0.1em]"
                style={{ color: brandColor }}
              >
                Latest
              </p>
            </div>
          </div>

          <div className="mt-5">
            <div
              className="h-2.5 rounded-full"
              style={{
                backgroundColor: theme.line,
              }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${cadencePct}%`,
                  backgroundColor: brandColor,
                }}
              />
            </div>

            <p
              className="mt-3 text-[11px] leading-5"
              style={{ color: theme.brown }}
            >
              These stores had purchased in at least 3 of the
              prior 4 months before missing the latest expected
              replenishment.
            </p>
          </div>
        </div>
      </div>

      {/* ================================================= */}
      {/* COMMERCIAL EXPOSURE */}
      {/* ================================================= */}

      <div
        className="mt-7 border-t pt-6"
        style={{ borderColor: theme.line }}
      >
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_300px]">
          <div>
            <p
              className="text-[11px] font-medium uppercase tracking-[0.16em]"
              style={{ color: theme.brown }}
            >
              Historical Volume At Risk
            </p>

            <p
              className="mt-2 text-[13px]"
              style={{ color: theme.brown }}
            >
              Combined monthly volume from these stores before
              the missed replenishment
            </p>

            <div className="mt-5 flex items-end gap-3">
              <span
                className="text-[38px] font-semibold tracking-[-0.05em]"
                style={{ color: brandColor }}
              >
                {formatNumber(avgMonthlyUnits4m)}
              </span>

              <span
                className="pb-1 text-[12px]"
                style={{ color: theme.brown }}
              >
                units / month
              </span>
            </div>

            <div
              className="mt-5 max-w-2xl border-l-[3px] pl-4"
              style={{ borderColor: brandColor }}
            >
              <p
                className="text-[13px] leading-6"
                style={{ color: theme.charcoal }}
              >
                This is a recent break from otherwise consistent
                ordering behavior, rather than a group of stores
                that had already been steadily declining.
              </p>
            </div>
          </div>

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
              Pattern At A Glance
            </p>

            <div className="mt-5 grid grid-cols-2 gap-x-5 gap-y-5">
              <div>
                <p
                  className="text-[24px] font-semibold tracking-[-0.04em]"
                  style={{ color: theme.charcoal }}
                >
                  {affectedStores}
                </p>

                <p
                  className="mt-1 text-[11px]"
                  style={{ color: theme.brown }}
                >
                  affected stores
                </p>
              </div>

              <div>
                <p
                  className="text-[24px] font-semibold tracking-[-0.04em]"
                  style={{ color: theme.charcoal }}
                >
                  {Number(avgReplenishedMonths ?? 0).toFixed(1)}
                </p>

                <p
                  className="mt-1 text-[11px]"
                  style={{ color: theme.brown }}
                >
                  avg prior months
                </p>
              </div>

              <div>
                <p
                  className="text-[24px] font-semibold tracking-[-0.04em]"
                  style={{ color: theme.charcoal }}
                >
                  {formatNumber(avgMonthlyUnits4m)}
                </p>

                <p
                  className="mt-1 text-[11px]"
                  style={{ color: theme.brown }}
                >
                  monthly units
                </p>
              </div>

              <div>
                <p
                  className="text-[24px] font-semibold tracking-[-0.04em]"
                  style={{
                    color: hasSingleSkuExposure
                      ? brandColor
                      : theme.charcoal,
                  }}
                >
                  {singleSkuStoreCount}
                </p>

                <p
                  className="mt-1 text-[11px]"
                  style={{ color: theme.brown }}
                >
                  single-SKU stores
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ================================================= */}
      {/* SINGLE SKU EXPOSURE */}
      {/* ================================================= */}

      {hasSingleSkuExposure && (
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
                Single-SKU Exposure
              </p>

              <p
                className="mt-2 max-w-xl text-[13px] leading-5"
                style={{ color: theme.brown }}
              >
                Some affected stores only carry one SKU, so a
                missed replenishment there can effectively mean
                the entire brand relationship goes quiet.
              </p>
            </div>

            <div className="text-right">
              <span
                className="text-[28px] font-semibold tracking-[-0.04em]"
                style={{ color: brandColor }}
              >
                {singleSkuStoreCount}
              </span>

              <p
                className="mt-1 text-[11px]"
                style={{ color: theme.brown }}
              >
                {singleSkuShare.toFixed(0)}% of affected stores
              </p>
            </div>
          </div>

          <div
            className="mt-5 h-3 rounded-full"
            style={{
              backgroundColor: theme.line,
            }}
          >
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.min(
                  Math.max(singleSkuShare, 0),
                  100
                )}%`,
                backgroundColor: brandColor,
              }}
            />
          </div>
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
