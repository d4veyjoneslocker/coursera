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

type DropoffSkuRiskProps = {
  sku: string

  affectedStores: number
  affectedStoreShare: number
  totalRecentBrandStores: number

  prior3mSkuUnits: number
  recent3mBrandUnits: number

  chain?: string | null
  dc?: string | null

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

export default function DropoffSkuRisk({
  sku,
  affectedStores,
  affectedStoreShare,
  totalRecentBrandStores,
  prior3mSkuUnits,
  recent3mBrandUnits,
  chain,
  dc,
  drilldown,
  theme,
}: DropoffSkuRiskProps) {
  const { org, skuColors } = useOrg()

  const brandColor =
    org?.primary_color ?? theme.brown

  const skuColor =
    skuColors?.[sku] ??
    skuColors?.[sku.trim().toUpperCase()] ??
    brandColor

  const affectedPct =
    Number(affectedStoreShare ?? 0) * 100

  const healthyBrandStores = Math.max(
    totalRecentBrandStores - affectedStores,
    0
  )

  const useActualStores =
    totalRecentBrandStores > 0 &&
    totalRecentBrandStores <= 24

  const visualTotal = useActualStores
    ? totalRecentBrandStores
    : 24

  const visualAffected = useActualStores
    ? affectedStores
    : Math.round(
        Math.min(
          Math.max(affectedStoreShare, 0),
          1
        ) * visualTotal
      )

  const hasConcentration =
    Boolean(chain) || Boolean(dc)

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
            SKU Drop-Off
          </p>

          <span style={{ color: theme.line }}>
            ·
          </span>

          <span
            className="text-[14px] font-semibold uppercase tracking-[0.04em]"
            style={{ color: theme.charcoal }}
          >
            {sku}
          </span>
        </div>

        <InsightDescription
          definition={insightDefinitions.dropoff_sku_risk}
        />
      </div>

      {/* ================================================= */}
      {/* PRIMARY STORY */}
      {/* ================================================= */}

      <div className="mt-7 grid grid-cols-1 gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        {/* LEFT */}
        <div>
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Active Stores That Dropped The SKU
          </p>

          <div className="mt-3 flex items-end gap-3">
            <p
              className="text-[52px] font-semibold leading-none tracking-[-0.06em]"
              style={{ color: skuColor }}
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
            These stores bought{" "}
            <strong>{sku}</strong> previously, but bought
            none in the latest 3 full months while continuing
            to buy the brand.
          </p>

          <div className="mt-5 flex items-center gap-3">
            <span
              className="text-[22px] font-semibold tracking-[-0.03em]"
              style={{ color: skuColor }}
            >
              {affectedPct.toFixed(0)}%
            </span>

            <span
              className="text-[13px]"
              style={{ color: theme.brown }}
            >
              of recent active brand stores
            </span>
          </div>
        </div>

        {/* RIGHT: STORE VISUAL */}
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
                Store Relationship
              </p>

              <p
                className="mt-2 text-[13px]"
                style={{ color: theme.brown }}
              >
                Still buying the brand, no longer buying this SKU
              </p>
            </div>

            <div className="text-right">
              <p
                className="text-[21px] font-semibold"
                style={{ color: theme.charcoal }}
              >
                {totalRecentBrandStores}
              </p>

              <p
                className="text-[10px] uppercase tracking-[0.12em]"
                style={{ color: theme.brown }}
              >
                active stores
              </p>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-2">
            {Array.from({ length: visualTotal }).map(
              (_, index) => {
                const isAffected =
                  index < visualAffected

                return (
                  <div
                    key={index}
                    className="h-4 w-4 rounded-[4px] border"
                    style={{
                      backgroundColor: isAffected
                        ? skuColor
                        : "transparent",
                      borderColor: isAffected
                        ? skuColor
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
                  backgroundColor: skuColor,
                }}
              />

              <span
                className="text-[12px]"
                style={{ color: theme.brown }}
              >
                {useActualStores
                  ? `${affectedStores} dropped ${sku}`
                  : `${affectedPct.toFixed(0)}% dropped ${sku}`}
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
                  ? `${healthyBrandStores} other active stores`
                  : `${Math.max(100 - affectedPct, 0).toFixed(0)}% unaffected`}
              </span>
            </div>
          </div>

          {!useActualStores &&
            totalRecentBrandStores > 0 && (
              <p
                className="mt-3 text-[10px]"
                style={{ color: theme.brown }}
              >
                Each square represents approximately{" "}
                {(totalRecentBrandStores / visualTotal).toFixed(1)} stores.
              </p>
            )}
        </div>
      </div>

      {/* ================================================= */}
      {/* SALES CONTEXT */}
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
              Before The Drop-Off
            </p>

            <p
              className="mt-2 text-[13px]"
              style={{ color: theme.brown }}
            >
              SKU volume from these same stores in the prior 3 months
            </p>

            <div className="mt-5 flex items-end gap-3">
              <span
                className="text-[36px] font-semibold tracking-[-0.05em]"
                style={{ color: skuColor }}
              >
                {formatNumber(prior3mSkuUnits)}
              </span>

              <span
                className="pb-1 text-[12px]"
                style={{ color: theme.brown }}
              >
                units of {sku}
              </span>
            </div>

            <div
              className="mt-5 max-w-2xl border-l-[3px] pl-4"
              style={{ borderColor: skuColor }}
            >
              <p
                className="text-[13px] leading-6"
                style={{ color: theme.charcoal }}
              >
                The store relationship is still active. The
                issue is isolated to this SKU rather than a
                complete loss of the account.
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
              Brand Activity Continues
            </p>

            <p
              className="mt-5 text-[34px] font-semibold tracking-[-0.045em]"
              style={{ color: theme.charcoal }}
            >
              {formatNumber(recent3mBrandUnits)}
            </p>

            <p
              className="mt-1 text-[11px]"
              style={{ color: theme.brown }}
            >
              recent brand units across affected stores
            </p>

            <div
              className="mt-5 border-t pt-4"
              style={{ borderColor: theme.line }}
            >
              <p
                className="text-[12px] leading-5"
                style={{ color: theme.brown }}
              >
                These accounts are still ordering other items,
                which makes them a practical SKU-specific
                follow-up list.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ================================================= */}
      {/* CONCENTRATION */}
      {/* ================================================= */}

      {hasConcentration && (
        <div
          className="mt-7 border-t pt-6"
          style={{ borderColor: theme.line }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Where The Drop-Off Is Concentrated
          </p>

          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {chain && (
              <div
                className="rounded-[16px] border px-5 py-4"
                style={{ borderColor: theme.line }}
              >
                <p
                  className="text-[10px] font-medium uppercase tracking-[0.13em]"
                  style={{ color: theme.brown }}
                >
                  Chain
                </p>

                <p
                  className="mt-2 text-[18px] font-semibold uppercase tracking-[-0.02em]"
                  style={{ color: theme.charcoal }}
                >
                  {chain}
                </p>

                <p
                  className="mt-2 text-[11px] leading-5"
                  style={{ color: theme.brown }}
                >
                  A meaningful share of the affected stores
                  sits within this chain.
                </p>
              </div>
            )}

            {dc && (
              <div
                className="rounded-[16px] border px-5 py-4"
                style={{ borderColor: theme.line }}
              >
                <p
                  className="text-[10px] font-medium uppercase tracking-[0.13em]"
                  style={{ color: theme.brown }}
                >
                  Distribution Center
                </p>

                <p
                  className="mt-2 text-[18px] font-semibold uppercase tracking-[-0.02em]"
                  style={{ color: theme.charcoal }}
                >
                  {dc}
                </p>

                <p
                  className="mt-2 text-[11px] leading-5"
                  style={{ color: theme.brown }}
                >
                  The affected stores also show meaningful
                  concentration through this DC.
                </p>
              </div>
            )}
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
