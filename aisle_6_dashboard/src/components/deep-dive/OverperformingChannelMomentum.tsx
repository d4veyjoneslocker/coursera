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

type MetricCardProps = {
  label: string
  value: string
  sublabel: string
  theme: Theme
}

function MetricCard({
  label,
  value,
  sublabel,
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

      <p
        className="mt-3 text-[12px] leading-5"
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

  /*
   * Use a common 0–100 scale rather than scaling each bar
   * relative to whichever one is larger.
   *
   * This makes 9% vs 15% visually mean 9% vs 15%.
   */
  const storeShareWidth = Math.min(Math.max(storeSharePct, 0), 100)
  const unitShareWidth = Math.min(Math.max(unitSharePct, 0), 100)

  return (
    <div
      className="rounded-[16px] border px-6 py-6"
      style={{
        backgroundColor: "#FFFEFB",
        borderColor: theme.line,
      }}
    >
      {/* ------------------------------------------------ */}
      {/* HEADER */}
      {/* ------------------------------------------------ */}

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

      {/* ------------------------------------------------ */}
      {/* MAIN STORY */}
      {/* ------------------------------------------------ */}

      <div
        className="mt-6 rounded-[20px] border px-5 py-5"
        style={{
          backgroundColor: "#FCFAF6",
          borderColor: theme.line,
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
          {channel} represents{" "}
          <strong>{storeSharePct.toFixed(0)}%</strong> of buying stores
          but generates{" "}
          <strong>{unitSharePct.toFixed(0)}%</strong> of recent units.
        </p>

        {/* ---------------------------------------------- */}
        {/* STORE SHARE */}
        {/* ---------------------------------------------- */}

        <div className="mt-7">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div>
              <p
                className="text-[13px] font-medium"
                style={{ color: theme.brown }}
              >
                Share of buying stores
              </p>
            </div>

            <span
              className="text-[15px] font-semibold"
              style={{ color: theme.charcoal }}
            >
              {storeSharePct.toFixed(0)}%
            </span>
          </div>

          <div
            className="h-3 overflow-hidden rounded-full"
            style={{ backgroundColor: "#EEEAE3" }}
          >
            <div
              className="h-full rounded-full"
              style={{
                width: `${storeShareWidth}%`,
                backgroundColor: "#C9C2B8",
              }}
            />
          </div>
        </div>

        {/* ---------------------------------------------- */}
        {/* UNIT SHARE */}
        {/* ---------------------------------------------- */}

        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between gap-3">
            <div>
              <p
                className="text-[13px] font-medium"
                style={{ color: theme.brown }}
              >
                Share of recent units
              </p>
            </div>

            <span
              className="text-[15px] font-semibold"
              style={{ color: theme.charcoal }}
            >
              {unitSharePct.toFixed(0)}%
            </span>
          </div>

          <div
            className="h-3 overflow-hidden rounded-full"
            style={{ backgroundColor: "#EEEAE3" }}
          >
            <div
              className="h-full rounded-full"
              style={{
                width: `${unitShareWidth}%`,
                backgroundColor: primaryColor,
              }}
            />
          </div>
        </div>

        {/* ---------------------------------------------- */}
        {/* INTERPRETATION */}
        {/* ---------------------------------------------- */}

        <div
          className="mt-6 flex items-center gap-3 rounded-[16px] border px-4 py-3"
          style={{
            backgroundColor: "#FFFEFB",
            borderColor: theme.line,
          }}
        >
          <div
            className="shrink-0 text-[24px] font-semibold tracking-[-0.04em]"
            style={{ color: theme.charcoal }}
          >
            {Number(returnOnDistributionIndex ?? 0).toFixed(1)}×
          </div>

          <p
            className="text-[13px] leading-5"
            style={{ color: theme.brown }}
          >
            more unit share than its share of buying stores would suggest
          </p>
        </div>

        <p
          className="mt-4 text-[11px]"
          style={{ color: "#9A8A7C" }}
        >
          Based on the last 3 full months
        </p>
      </div>

      {/* ------------------------------------------------ */}
      {/* SUPPORTING EVIDENCE */}
      {/* ------------------------------------------------ */}

      <div className="mt-4">
        <p
          className="mb-3 text-[11px] font-medium uppercase tracking-[0.16em]"
          style={{ color: "#9A8A7C" }}
        >
          Supporting Signals
        </p>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <MetricCard
            label="Higher Velocity"
            value={`${velocityPct >= 0 ? "+" : ""}${velocityPct.toFixed(0)}%`}
            sublabel="Vs filtered business average"
            theme={theme}
          />

          <MetricCard
            label="Reorder Rate"
            value={`${reorderPct.toFixed(0)}%`}
            sublabel="Recent 3-month reorder rate"
            theme={theme}
          />

          <MetricCard
            label="Unit Share Growth"
            value={`${unitShareChangePts >= 0 ? "+" : ""}${unitShareChangePts.toFixed(1)} pts`}
            sublabel="Vs prior 3 months"
            theme={theme}
          />
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