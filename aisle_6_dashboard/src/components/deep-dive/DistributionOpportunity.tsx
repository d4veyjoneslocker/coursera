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

type MetricCardProps = {
  label: string
  value: string
  theme: Theme
}

function MetricCard({
  label,
  value,
  theme,
}: MetricCardProps) {
  return (
    <div
      className="rounded-[20px] border px-5 py-5"
      style={{
        backgroundColor: "#FFFEFB",
        borderColor: theme.line,
      }}
    >
      <p
        className="text-[11px] font-medium uppercase tracking-[0.16em]"
        style={{ color: "#9A8A7C" }}
      >
        {label}
      </p>

      <p
        className="mt-3 text-[30px] font-semibold leading-none tracking-[-0.04em]"
        style={{ color: theme.charcoal }}
      >
        {value}
      </p>
    </div>
  )
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

  const primaryColor = org?.primary_color ?? "#92B9DC"

  const totalStores = currentStores + opportunityStores

  const currentStorePct =
    totalStores > 0 ? (currentStores / totalStores) * 100 : 0

  const opportunityStorePct =
    totalStores > 0 ? (opportunityStores / totalStores) * 100 : 0

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
      {/* Header */}
        <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
            <p
            className="text-[13px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: theme.brown }}
            >
            Distribution Opportunity
            </p>

            <span
            className="text-[13px]"
            style={{ color: "#C8BEB4" }}
            >
            ·
            </span>

            <span
            className="text-[14px] font-semibold uppercase tracking-[0.04em]"
            style={{ color: skuColor }}
            >
            {sku}
            </span>

            <span
            className="text-[13px]"
            style={{ color: "#C8BEB4" }}
            >
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
            definition={insightDefinitions.distribution_opportunity}
        />
        </div>
        
      {/* ------------------------------------------------ */}
      {/* KPI ROW */}
      {/* ------------------------------------------------ */}

      <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
        <MetricCard
          label="Opportunity stores"
          value={formatNumber(opportunityStores)}
          theme={theme}
        />

        <MetricCard
          label="Annualized opportunity"
          value={`${formatCompact(annualizedOpportunityUnits)} units`}
          theme={theme}
        />

        <MetricCard
          label="Units / store / week"
          value={Number(averageVelocity ?? 0).toFixed(1)}
          theme={theme}
        />
      </div>

      {/* ------------------------------------------------ */}
      {/* VISUALS */}
      {/* ------------------------------------------------ */}

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">

        {/* ---------------------------------------------- */}
        {/* DISTRIBUTION COVERAGE */}
        {/* ---------------------------------------------- */}

        <div
          className="rounded-[20px] border px-5 py-5"
          style={{
            backgroundColor: "#FCFAF6",
            borderColor: theme.line,
          }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: "#9A8A7C" }}
          >
            Distribution Coverage
          </p>

          <p
            className="mt-2 text-[14px]"
            style={{ color: theme.brown }}
          >
            {formatNumber(totalStores)} {chain} stores currently buy the brand
          </p>

          {/* Stacked distribution bar */}
          <div
            className="mt-6 flex h-4 w-full overflow-hidden rounded-full"
            style={{ backgroundColor: "#EEEAE3" }}
          >
            <div
              className="h-full"
              style={{
                width: `${currentStorePct}%`,
                backgroundColor: primaryColor,
              }}
            />

            <div
              className="h-full"
              style={{
                width: `${opportunityStorePct}%`,
                backgroundColor: "#D8D2C8",
              }}
            />
          </div>

          {/* Distribution labels */}
          <div className="mt-4 flex items-start justify-between gap-5">

            <div>
              <div className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: primaryColor }}
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
                  style={{ backgroundColor: "#D8D2C8" }}
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
        </div>

        {/* ---------------------------------------------- */}
        {/* BRAND PURCHASE LIFT */}
        {/* ---------------------------------------------- */}

        <div
        className="rounded-[20px] border px-5 py-5"
        style={{
            backgroundColor: "#FCFAF6",
            borderColor: theme.line,
        }}
        >
        <div className="flex items-start justify-between gap-4">
            <div>
            <p
                className="text-[11px] font-medium uppercase tracking-[0.16em]"
                style={{ color: "#9A8A7C" }}
            >
                Brand Purchase Lift
            </p>

            <p
                className="mt-2 text-[14px]"
                style={{ color: theme.brown }}
            >
                Stores carrying {sku} buy more total brand units per store
            </p>
            </div>

            <div className="shrink-0 rounded-full bg-[#EAF3DE] px-3 py-1 text-[13px] font-semibold text-[#3B6D11]">
            ↑ {Number(salesLiftPct ?? 0).toFixed(0)}%
            </div>
        </div>

        <div className="mt-6 space-y-5">

            {/* Carrying */}
            <div>
            <div className="mb-2 flex items-center justify-between gap-3">
                <span
                className="text-[12px] font-medium"
                style={{ color: theme.brown }}
                >
                Stores carrying {sku}
                </span>

                <span
                className="text-[13px] font-semibold"
                style={{ color: theme.charcoal }}
                >
                {Number(carryingBrandUnits ?? 0).toFixed(1)}
                </span>
            </div>

            <div
                className="h-3 overflow-hidden rounded-full"
                style={{ backgroundColor: "#EEEAE3" }}
            >
                <div
                className="h-full rounded-full"
                style={{
                    width: `${carryingWidth}%`,
                    backgroundColor: primaryColor,
                }}
                />
            </div>
            </div>

            {/* Not carrying */}
            <div>
            <div className="mb-2 flex items-center justify-between gap-3">
                <span
                className="text-[12px] font-medium"
                style={{ color: theme.brown }}
                >
                Stores not carrying {sku}
                </span>

                <span
                className="text-[13px] font-semibold"
                style={{ color: theme.charcoal }}
                >
                {Number(nonCarryingBrandUnits ?? 0).toFixed(1)}
                </span>
            </div>

            <div
                className="h-3 overflow-hidden rounded-full"
                style={{ backgroundColor: "#EEEAE3" }}
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
            Average total brand units purchased per store · last 3 months
        </p>
        </div>

      </div>

      {/* ------------------------------------------------ */}
      {/* CTA */}
      {/* ------------------------------------------------ */}

      {drilldown && (
        <div className="mt-4">
          <a
            href={drilldown.href}
            className="inline-flex rounded-full border border-black/10 bg-[#F6F2EA] px-4 py-2 text-sm font-medium text-[#343332] hover:bg-[#E9E2C8]"
          >
            {drilldown.label} →
          </a>
        </div>
      )}
    </div>
  )
}