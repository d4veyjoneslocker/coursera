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

type OverperformingChannelMomentumProps = {
  channel: string

  recentStoreShare: number
  recentUnitShare: number
  returnOnDistributionIndex: number

  velocityOutperformancePct: number
  recentReorderRate: number
  unitShareChangeAbs: number

  drilldown?: {
    label: string
    href: string
  }

  theme: Theme
}

type SupportingMetricProps = {
  label: string
  value: string
  sublabel: string
  theme: Theme
}

function SupportingMetric({
  label,
  value,
  sublabel,
  theme,
}: SupportingMetricProps) {
  return (
    <div className="min-w-0 flex-1 px-5 py-2">
      <p
        className="text-[11px] font-medium uppercase tracking-[0.16em]"
        style={{ color: "#9A8A7C" }}
      >
        {label}
      </p>

      <p
        className="mt-2 text-[28px] font-semibold leading-none tracking-[-0.04em]"
        style={{ color: theme.charcoal }}
      >
        {value}
      </p>

      <p
        className="mt-2 text-[12px] leading-5"
        style={{ color: theme.brown }}
      >
        {sublabel}
      </p>
    </div>
  )
}

export default function OverperformingChannelMomentum({
  channel,
  recentStoreShare,
  recentUnitShare,
  returnOnDistributionIndex,
  velocityOutperformancePct,
  recentReorderRate,
  unitShareChangeAbs,
  drilldown,
  theme,
}: OverperformingChannelMomentumProps) {
  const { org } = useOrg()

  const primaryColor = org?.primary_color ?? "#92B9DC"

  const storeSharePct = Number(recentStoreShare ?? 0) * 100
  const unitSharePct = Number(recentUnitShare ?? 0) * 100

  const velocityPct =
    Number(velocityOutperformancePct ?? 0) * 100

  const reorderPct =
    Number(recentReorderRate ?? 0) * 100

  const unitShareChangePts =
    Number(unitShareChangeAbs ?? 0) * 100

  return (
    <div
      className="rounded-[16px] border px-6 py-6"
      style={{
        backgroundColor: "#FFFEFB",
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
            Overperforming Channel
          </p>

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
            {channel}
          </span>
        </div>

        <InsightDescription
          definition={
            insightDefinitions.overperforming_channel_momentum
          }
        />
      </div>

      {/* HERO */}
      <div
        className="mt-6 rounded-[20px] px-6 py-7"
        style={{
          backgroundColor: "#FCFAF6",
        }}
      >
        <p
          className="text-[11px] font-medium uppercase tracking-[0.16em]"
          style={{ color: "#9A8A7C" }}
        >
          Punching Above Its Weight
        </p>

        <p
          className="mt-2 text-[17px] font-medium leading-7"
          style={{ color: theme.charcoal }}
        >
          {channel} generates disproportionately more unit volume
          than its share of buying stores.
        </p>

        {/* FOOTPRINT → OUTPUT VISUAL */}
        <div className="mt-8">
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-5">

            {/* LEFT */}
            <div className="text-center">
              <p
                className="text-[42px] font-semibold leading-none tracking-[-0.05em]"
                style={{ color: theme.charcoal }}
              >
                {storeSharePct.toFixed(0)}%
              </p>

              <p
                className="mt-2 text-[11px] font-medium uppercase tracking-[0.15em]"
                style={{ color: "#9A8A7C" }}
              >
                Of Buying Stores
              </p>

              <div className="mt-4 flex justify-center">
                <div
                  className="h-4 w-4 rounded-full"
                  style={{ backgroundColor: "#C9C2B8" }}
                />
              </div>

              <p
                className="mt-2 text-[11px]"
                style={{ color: "#9A8A7C" }}
              >
                Footprint
              </p>
            </div>

            {/* CONNECTOR */}
            <div className="flex min-w-[180px] items-center">
              <div
                className="h-px flex-1"
                style={{ backgroundColor: "#D8D2C8" }}
              />

              <div
                className="mx-3 flex h-10 w-10 items-center justify-center rounded-full border text-[18px]"
                style={{
                  backgroundColor: "#FFFEFB",
                  borderColor: theme.line,
                  color: primaryColor,
                }}
              >
                →
              </div>

              <div
                className="h-px flex-1"
                style={{ backgroundColor: "#D8D2C8" }}
              />
            </div>

            {/* RIGHT */}
            <div className="text-center">
              <p
                className="text-[42px] font-semibold leading-none tracking-[-0.05em]"
                style={{ color: primaryColor }}
              >
                {unitSharePct.toFixed(0)}%
              </p>

              <p
                className="mt-2 text-[11px] font-medium uppercase tracking-[0.15em]"
                style={{ color: "#9A8A7C" }}
              >
                Of Recent Units
              </p>

              <div className="mt-4 flex justify-center">
                <div
                  className="h-4 w-4 rounded-full"
                  style={{ backgroundColor: primaryColor }}
                />
              </div>

              <p
                className="mt-2 text-[11px]"
                style={{ color: "#9A8A7C" }}
              >
                Output
              </p>
            </div>
          </div>

          {/* INTERPRETATION */}
          <div className="mt-7 text-center">
            <div
              className="inline-flex items-baseline gap-2 rounded-full px-4 py-2"
              style={{
                backgroundColor: "#EAF3DE",
                color: "#3B6D11",
              }}
            >
              <span className="text-[22px] font-semibold tracking-[-0.03em]">
                {Number(returnOnDistributionIndex ?? 0).toFixed(1)}×
              </span>

              <span className="text-[12px] font-medium">
                expected unit share
              </span>
            </div>

            <p
              className="mt-2 text-[12px]"
              style={{ color: theme.brown }}
            >
              based on its share of recent buying stores
            </p>
          </div>
        </div>

        <p
          className="mt-6 text-center text-[11px]"
          style={{ color: "#9A8A7C" }}
        >
          Based on the last 3 full months
        </p>
      </div>

      {/* SUPPORTING SIGNALS */}
      <div className="mt-5">
        <p
          className="mb-3 text-[11px] font-medium uppercase tracking-[0.16em]"
          style={{ color: "#9A8A7C" }}
        >
          Supporting Signals
        </p>

        <div
          className="flex flex-col overflow-hidden rounded-[18px] border md:flex-row"
          style={{
            borderColor: theme.line,
            backgroundColor: "#FFFEFB",
          }}
        >
          <SupportingMetric
            label="Higher Velocity"
            value={`${velocityPct >= 0 ? "+" : ""}${velocityPct.toFixed(0)}%`}
            sublabel="Vs filtered business average"
            theme={theme}
          />

          <div
            className="hidden w-px self-stretch md:block"
            style={{ backgroundColor: theme.line }}
          />

          <SupportingMetric
            label="Reorder Rate"
            value={`${reorderPct.toFixed(0)}%`}
            sublabel="Recent 3-month reorder rate"
            theme={theme}
          />

          <div
            className="hidden w-px self-stretch md:block"
            style={{ backgroundColor: theme.line }}
          />

          <SupportingMetric
            label="Unit Share Growth"
            value={`${unitShareChangePts >= 0 ? "+" : ""}${unitShareChangePts.toFixed(1)} pts`}
            sublabel="Vs prior 3 months"
            theme={theme}
          />
        </div>
      </div>

      {/* CTA */}
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