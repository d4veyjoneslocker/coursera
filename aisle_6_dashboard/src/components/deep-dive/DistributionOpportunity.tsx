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

type DistributionOpportunityProps = {
  sku: string
  chain: string

  currentStores: number
  opportunityStores: number

  annualizedOpportunityUnits: number
  averageVelocity: number

  carryingBrandUnits: number
  nonCarryingBrandUnits: number
  salesLiftPct: number

  drilldown?: {
    label: string
    href: string
  }

  theme: Theme
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value)
}

function formatCompact(value: number) {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`
  }

  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }

  return formatNumber(value)
}

export default function DistributionOpportunity({
  sku,
  chain,
  currentStores,
  opportunityStores,
  annualizedOpportunityUnits,
  averageVelocity,
  carryingBrandUnits,
  nonCarryingBrandUnits,
  salesLiftPct,
  drilldown,
  theme,
}: DistributionOpportunityProps) {
  const { org, skuColors } = useOrg()

  const skuColor =
    skuColors?.[sku] ??
    skuColors?.[sku.trim().toUpperCase()] ??
    "#92B9DC"

  const primaryColor =
    org?.primary_color ?? "#92B9DC"

  const totalStores =
    currentStores + opportunityStores

  const currentStorePct =
    totalStores > 0
      ? (currentStores / totalStores) * 100
      : 0

  const opportunityStorePct =
    totalStores > 0
      ? (opportunityStores / totalStores) * 100
      : 0

  const maxBrandUnits = Math.max(
    carryingBrandUnits,
    nonCarryingBrandUnits,
    1
  )

  const carryingWidth =
    (carryingBrandUnits / maxBrandUnits) * 100

  const nonCarryingWidth =
    (nonCarryingBrandUnits / maxBrandUnits) * 100

  return (
    <div
      className="rounded-[16px] border px-6 py-6"
      style={{
        backgroundColor: "#FFFEFB",
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
            Distribution Opportunity
          </p>

          <span style={{ color: "#C8BEB4" }}>
            ·
          </span>

          <span
            className="text-[14px] font-semibold uppercase tracking-[0.04em]"
            style={{ color: skuColor }}
          >
            {sku}
          </span>

          <span style={{ color: "#C8BEB4" }}>
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
          definition={
            insightDefinitions.distribution_opportunity
          }
        />
      </div>

      {/* ================================================= */}
      {/* PRIMARY STORY */}
      {/* ================================================= */}

      <div className="mt-7 grid grid-cols-1 gap-8 lg:grid-cols-[0.9fr_1.1fr]">

        {/* LEFT: MAIN OPPORTUNITY */}
        <div>
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Untapped Distribution
          </p>

          <div className="mt-3 flex items-end gap-3">
            <p
              className="text-[48px] font-semibold leading-none tracking-[-0.05em]"
              style={{ color: skuColor }}
            >
              {formatNumber(opportunityStores)}
            </p>

            <p
              className="pb-1 text-[14px]"
              style={{ color: theme.brown }}
            >
              opportunity stores
            </p>
          </div>

          <p
            className="mt-5 max-w-md text-[16px] leading-7"
            style={{ color: theme.charcoal }}
          >
            These {chain} stores already buy your brand,
            but do not currently carry{" "}
            <strong>{sku}</strong>.
          </p>

          <div className="mt-5 flex items-center gap-3">
            <span
              className="text-[22px] font-semibold tracking-[-0.03em]"
              style={{ color: skuColor }}
            >
              +{formatCompact(annualizedOpportunityUnits)}
            </span>

            <span
              className="text-[13px]"
              style={{ color: theme.brown }}
            >
              annualized unit opportunity
            </span>
          </div>
        </div>

        {/* RIGHT: DISTRIBUTION COVERAGE */}
        <div
          className="rounded-[18px] border px-5 py-5"
          style={{
            backgroundColor: "#FFFEFB",
            borderColor: theme.line,
          }}
        >
          <div className="flex items-center justify-between gap-4">
            <p
              className="text-[11px] font-medium uppercase tracking-[0.16em]"
              style={{ color: theme.brown }}
            >
              Distribution Coverage
            </p>

            <p
              className="text-[12px]"
              style={{ color: theme.brown }}
            >
              {formatNumber(totalStores)} brand-buying stores
            </p>
          </div>

          {/* COVERAGE BAR */}
          <div
            className="mt-6 flex h-4 w-full overflow-hidden rounded-full"
            style={{ backgroundColor: "#EEEAE3" }}
          >
            {/* Already carrying = grey */}
            <div
              className="h-full"
              style={{
                width: `${currentStorePct}%`,
                backgroundColor: "#D8D2C8",
              }}
            />

            {/* Opportunity = blue */}
            <div
              className="h-full"
              style={{
                width: `${opportunityStorePct}%`,
                backgroundColor: skuColor,
              }}
            />
          </div>

          {/* COVERAGE LABELS */}
          <div className="mt-4 flex items-start justify-between gap-5">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{
                    backgroundColor: "#D8D2C8",
                  }}
                />

                <span
                  className="text-[13px] font-medium"
                  style={{ color: theme.charcoal }}
                >
                  {formatNumber(currentStores)} carrying
                </span>
              </div>

              <p
                className="ml-[18px] mt-1 text-[11px]"
                style={{ color: "#9A8A7C" }}
              >
                {currentStorePct.toFixed(0)}% of stores
              </p>
            </div>

            <div>
              <div className="flex items-center justify-end gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{
                    backgroundColor: skuColor,
                  }}
                />

                <span
                  className="text-[13px] font-medium"
                  style={{ color: theme.charcoal }}
                >
                  {formatNumber(opportunityStores)} opportunity
                </span>
              </div>

              <p
                className="mt-1 text-right text-[11px]"
                style={{ color: "#9A8A7C" }}
              >
                {opportunityStorePct.toFixed(0)}% of stores
              </p>
            </div>
          </div>

          <p
            className="mt-6 text-[12px] leading-5"
            style={{ color: theme.brown }}
          >
            Opportunity stores are already proven buyers
            of the brand, making this a lower-friction
            distribution expansion.
          </p>
        </div>
      </div>

      {/* ================================================= */}
      {/* SUPPORTING EVIDENCE */}
      {/* ================================================= */}

      <div
        className="mt-7 border-t pt-6"
        style={{ borderColor: theme.line }}
      >
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_320px]">

          {/* LEFT: BRAND PURCHASE LIFT */}
          <div>
            <div className="flex items-end justify-between gap-5">
              <div>
                <p
                  className="text-[11px] font-medium uppercase tracking-[0.16em]"
                  style={{ color: theme.brown }}
                >
                  The Impact of {sku}
                </p>

                <p
                  className="mt-2 text-[13px]"
                  style={{ color: theme.brown }}
                >
                  Stores carrying {sku} buy more of the
                  brand overall
                </p>
              </div>

              {/* Lift stays attached to bars */}
              <div className="shrink-0 text-right">
                <span
                  className="text-[24px] font-semibold"
                  style={{ color: skuColor }}
                >
                  +{Number(salesLiftPct ?? 0).toFixed(0)}%
                </span>

                <p
                  className="mt-1 text-[11px]"
                  style={{ color: theme.brown }}
                >
                  brand purchase lift
                </p>
              </div>
            </div>

            {/* ALWAYS STACKED */}
            <div className="mt-6 space-y-6">

              {/* Carrying */}
              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span
                    className="text-[12px] font-medium"
                    style={{ color: theme.charcoal }}
                  >
                    Stores carrying {sku}
                  </span>

                  <span
                    className="text-[13px] font-semibold"
                    style={{ color: theme.charcoal }}
                  >
                    {Number(
                      carryingBrandUnits ?? 0
                    ).toFixed(1)}
                  </span>
                </div>

                <div
                  className="h-3 overflow-hidden rounded-full"
                  style={{
                    backgroundColor: "#EEEAE3",
                  }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${carryingWidth}%`,
                      backgroundColor: skuColor,
                    }}
                  />
                </div>
              </div>

              {/* Not carrying */}
              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span
                    className="text-[12px] font-medium"
                    style={{ color: theme.charcoal }}
                  >
                    Stores not carrying {sku}
                  </span>

                  <span
                    className="text-[13px] font-semibold"
                    style={{ color: theme.charcoal }}
                  >
                    {Number(
                      nonCarryingBrandUnits ?? 0
                    ).toFixed(1)}
                  </span>
                </div>

                <div
                  className="h-3 overflow-hidden rounded-full"
                  style={{
                    backgroundColor: "#EEEAE3",
                  }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${nonCarryingWidth}%`,
                      backgroundColor: "#C9C2B8",
                    }}
                  />
                </div>
              </div>
            </div>

            <p
              className="mt-4 text-[11px]"
              style={{ color: "#9A8A7C" }}
            >
              Average total brand units purchased per
              store · last 3 months
            </p>
          </div>

          {/* RIGHT: NAPKIN MATH */}
          <div
            className="rounded-[16px] border px-5 py-5"
            style={{
              backgroundColor: "#FCFAF6",
              borderColor: theme.line,
            }}
          >
            <p
              className="text-[10px] font-medium uppercase tracking-[0.16em]"
              style={{ color: "#9A8A7C" }}
            >
              Opportunity Math
            </p>

            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between gap-4">
                <span
                  className="text-[13px]"
                  style={{ color: theme.brown }}
                >
                  Opportunity stores
                </span>

                <span
                  className="text-[13px] font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  {formatNumber(opportunityStores)}
                </span>
              </div>

              <div className="flex items-center justify-between gap-4">
                <span
                  className="text-[13px]"
                  style={{ color: theme.brown }}
                >
                  × velocity at carrying stores
                </span>

                <span
                  className="text-[13px] font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  {Number(
                    averageVelocity ?? 0
                  ).toFixed(1)}
                </span>
              </div>

              <div className="flex items-center justify-between gap-4">
                <span
                  className="text-[13px]"
                  style={{ color: theme.brown }}
                >
                  × weeks
                </span>

                <span
                  className="text-[13px] font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  52
                </span>
              </div>
            </div>

            <div
              className="mt-4 border-t pt-4"
              style={{ borderColor: theme.line }}
            >
              <div className="flex items-end justify-between gap-4">
                <span
                  className="text-[11px] font-medium uppercase tracking-[0.12em]"
                  style={{ color: theme.brown }}
                >
                  Annualized
                </span>

                <span
                  className="text-[25px] font-semibold tracking-[-0.04em]"
                  style={{ color: skuColor }}
                >
                  {formatCompact(
                    annualizedOpportunityUnits
                  )}
                </span>
              </div>

              <p
                className="mt-1 text-right text-[11px]"
                style={{ color: "#9A8A7C" }}
              >
                units
              </p>
            </div>
          </div>
        </div>
      </div>

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