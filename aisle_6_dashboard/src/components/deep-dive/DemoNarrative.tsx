"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"

type DriverKey = "new" | "ramping" | "mature"

export default function BusinessNarrativeSummary() {
  const theme = {
    surface: "#FFFEFB",
    line: "#DED8CF",
    brown: "#8C6F5A",
    charcoal: "#343332",
    muted: "#9A8A7C",
    blue: "#79A8CF",
    blueDark: "#5E8EAF",
    blueLight: "#ADC9DD",
    red: "#A96552",
    redLight: "#C99B8D",
    track: "#EEEAE3",
  }

  const netChange = 19320
  const newImpact = 49024
  const rampingImpact = -18486
  const matureImpact = -11218

  const [openDriver, setOpenDriver] =
    useState<DriverKey | null>(null)

  const maxImpact = Math.max(
    Math.abs(newImpact),
    Math.abs(rampingImpact),
    Math.abs(matureImpact)
  )

  const getWidth = (value: number) =>
    (Math.abs(value) / maxImpact) * 47

  function toggle(driver: DriverKey) {
    setOpenDriver((current) =>
      current === driver ? null : driver
    )
  }

  function formatCompact(value: number) {
    const sign = value > 0 ? "+" : value < 0 ? "−" : ""
    const abs = Math.abs(value)

    if (abs >= 1000) {
      return `${sign}${(abs / 1000).toFixed(1)}K`
    }

    return `${sign}${abs.toFixed(0)}`
  }

  return (
    <div>
      {/* ================================================= */}
      {/* TOP SUMMARY */}
      {/* ================================================= */}

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        {/* HERO */}

        <div>
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Net Unit Change
          </p>

          <div className="mt-3 flex items-end gap-3">
            <p
              className="text-[52px] font-semibold leading-none tracking-[-0.06em]"
              style={{ color: theme.blue }}
            >
              {formatCompact(netChange)}
            </p>

            <p
              className="pb-1 text-[14px]"
              style={{ color: theme.brown }}
            >
              units
            </p>
          </div>

          <p
            className="mt-5 max-w-md text-[16px] leading-7"
            style={{ color: theme.charcoal }}
          >
            <strong>
              New distribution is masking weakness
            </strong>{" "}
            in the existing business.
          </p>

          <p
            className="mt-3 max-w-md text-[13px] leading-6"
            style={{ color: theme.brown }}
          >
            New placements added{" "}
            <strong style={{ color: theme.charcoal }}>
              +49.0K units
            </strong>
            , more than offsetting declines from recent
            launches and established placements.
          </p>
        </div>

        {/* DECOMPOSITION */}

        <div
          className="rounded-[18px] border px-5 py-5"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p
                className="text-[11px] font-medium uppercase tracking-[0.16em]"
                style={{ color: theme.brown }}
              >
                Change Decomposition
              </p>

              <p
                className="mt-2 text-[13px]"
                style={{ color: theme.brown }}
              >
                What added to — and pulled against — growth
              </p>
            </div>

            <p
              className="text-[12px] font-medium"
              style={{ color: theme.charcoal }}
            >
              Net {formatCompact(netChange)}
            </p>
          </div>

          <div className="mt-7">
            <div className="grid grid-cols-[110px_1fr] gap-3">
              <div />

              <div
                className="grid grid-cols-2 text-[9px] font-medium uppercase tracking-[0.12em]"
                style={{ color: theme.muted }}
              >
                <span className="pr-3 text-right">
                  Drag
                </span>

                <span className="pl-3">
                  Contribution
                </span>
              </div>
            </div>

            <div className="mt-2 space-y-5">
              <ContributionRow
                label="New"
                sublabel="distribution"
                value={newImpact}
                width={getWidth(newImpact)}
                color={theme.blue}
                theme={theme}
              />

              <ContributionRow
                label="Ramping"
                sublabel="recent launches"
                value={rampingImpact}
                width={getWidth(rampingImpact)}
                color={theme.red}
                theme={theme}
              />

              <ContributionRow
                label="Mature"
                sublabel="established"
                value={matureImpact}
                width={getWidth(matureImpact)}
                color={theme.redLight}
                theme={theme}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ================================================= */}
      {/* EXPANDABLE STORIES */}
      {/* ================================================= */}

      <div
        className="mt-8 border-t"
        style={{ borderColor: theme.line }}
      >
        {/* NEW */}

        <StoryRow
          sentence={
            <>
              New distribution added{" "}
              <strong style={{ color: theme.blue }}>
                +49.0K units
              </strong>
              , led by The Fresh Market.
            </>
          }
          isOpen={openDriver === "new"}
          onClick={() => toggle("new")}
          theme={theme}
        >
          <div>
            <p
              className="mb-5 text-[10px] font-medium uppercase tracking-[0.14em]"
              style={{ color: theme.muted }}
            >
              New Placement Contribution
            </p>

            <div className="space-y-5">
              <EntityBar
                label="The Fresh Market"
                value="+28.1K"
                width={100}
                color={theme.blue}
                theme={theme}
              />

              <EntityBar
                label="Safeway"
                value="+12.4K"
                width={44}
                color="#9CBED6"
                theme={theme}
              />

              <EntityBar
                label="Target"
                value="+6.7K"
                width={24}
                color="#BCD1E0"
                theme={theme}
              />
            </div>
          </div>
        </StoryRow>

        {/* RAMPING */}

        <StoryRow
          sentence={
            <>
              Recent launches declined{" "}
              <strong style={{ color: theme.red }}>
                −18.5K
              </strong>
              , but reorder behavior remains healthy.
            </>
          }
          isOpen={openDriver === "ramping"}
          onClick={() => toggle("ramping")}
          theme={theme}
        >
          <div>
            {/* TOP METRICS */}

            <div className="grid grid-cols-2 gap-5">
              <BigMetric
                value="91.4%"
                label="placements reordered"
                theme={theme}
              />

              <BigMetric
                value="2.7×"
                label="avg reorders"
                theme={theme}
              />
            </div>

            {/* ENTITY COMPARISON */}

            <div className="mt-7 grid grid-cols-1 gap-5 md:grid-cols-2">
              {/* SPROUTS */}

              <div
                className="border-l-[3px] pl-4"
                style={{
                  borderColor: "#CFC8BF",
                }}
              >
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <p
                        className="text-[13px] font-medium"
                        style={{
                            color: theme.charcoal,
                        }}
                        >
                        Sprouts
                        </p>
                    </div>

                    <div className="text-right">
                        <p
                        className="text-[20px] font-semibold"
                        style={{ color: theme.charcoal }}
                        >
                        97.2%
                        </p>

                        <p
                        className="text-[10px]"
                        style={{ color: theme.muted }}
                        >
                        reordered
                        </p>
                    </div>
                    </div>

                <div
                  className="mt-4 h-2 overflow-hidden rounded-[2px]"
                  style={{
                    backgroundColor: theme.track,
                  }}
                >
                  <div
                    className="h-full rounded-[2px]"
                    style={{
                      width: "100%",
                      backgroundColor: "#C99B8D",
                    }}
                  />
                </div>
              </div>

              {/* GOOD EARTH */}

              <div
                className="border-l-[3px] pl-4"
                style={{
                  borderColor: theme.red,
                }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p
                      className="text-[10px] font-semibold uppercase tracking-[0.13em]"
                      style={{ color: theme.red }}
                    >
                      Watch
                    </p>

                    <p
                      className="mt-1 text-[13px] font-medium"
                      style={{
                        color: theme.charcoal,
                      }}
                    >
                      Good Earth Markets
                    </p>
                  </div>

                  <div className="text-right">
                    <p
                      className="text-[20px] font-semibold"
                      style={{ color: theme.red }}
                    >
                      8.3%
                    </p>

                    <p
                      className="text-[10px]"
                      style={{ color: theme.muted }}
                    >
                      reordered
                    </p>
                  </div>
                </div>

                <div
                  className="mt-4 h-2 overflow-hidden rounded-[2px]"
                  style={{
                    backgroundColor: theme.track,
                  }}
                >
                  <div
                    className="h-full rounded-[2px]"
                    style={{
                      width: "8.3%",
                      backgroundColor: theme.red,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </StoryRow>

        {/* MATURE */}

        <StoryRow
          sentence={
            <>
              Established placements fell{" "}
              <strong style={{ color: theme.red }}>
                −11.2K
              </strong>{" "}
              as VPO weakened{" "}
              <strong style={{ color: theme.red }}>
                18.7%
              </strong>
              .
            </>
          }
          isOpen={openDriver === "mature"}
          onClick={() => toggle("mature")}
          theme={theme}
        >
          <div>
            {/* VPO HERO */}

            <div className="flex items-end gap-3">
              <p
                className="text-[36px] font-semibold leading-none tracking-[-0.05em]"
                style={{ color: theme.red }}
              >
                −18.7%
              </p>

              <p
                className="pb-1 text-[11px] font-medium uppercase tracking-[0.12em]"
                style={{ color: theme.muted }}
              >
                VPO
              </p>
            </div>

            {/* ENTITY BARS */}

            <div className="mt-7 space-y-5">
              <DualMetricBar
                label="Whole Foods"
                impact="−9.4K"
                metric="VPO −31.6%"
                width={100}
                negative
                theme={theme}
              />

              <DualMetricBar
                label="Sprouts"
                impact="−2.6K"
                metric="VPO −14.2%"
                width={45}
                negative
                theme={theme}
              />

              <DualMetricBar
                label="ShopRite"
                impact="+1.8K"
                metric="VPO +12.6%"
                width={30}
                theme={theme}
              />
            </div>
          </div>
        </StoryRow>
      </div>
    </div>
  )
}

/* ================================================= */
/* COLLAPSED / EXPANDED STORY ROW */
/* ================================================= */

function StoryRow({
  sentence,
  isOpen,
  onClick,
  children,
  theme,
}: {
  sentence: React.ReactNode
  isOpen: boolean
  onClick: () => void
  children: React.ReactNode
  theme: any
}) {
  return (
    <div
      className="border-b last:border-b-0"
      style={{ borderColor: theme.line }}
    >
      <button
        type="button"
        onClick={onClick}
        className="flex w-full items-center justify-between gap-6 py-5 text-left"
      >
        <p
          className="text-[17px] font-medium leading-7"
          style={{ color: theme.charcoal }}
        >
          {sentence}
        </p>

        <ChevronDown
          size={17}
          strokeWidth={1.8}
          className="shrink-0"
          style={{
            color: theme.muted,
            transition: "transform 160ms ease",
            transform: isOpen
              ? "rotate(180deg)"
              : "rotate(0deg)",
          }}
        />
      </button>

      {isOpen && (
        <div className="pb-7">
          <div
            className="border-t pt-6"
            style={{ borderColor: theme.line }}
          >
            {children}
          </div>
        </div>
      )}
    </div>
  )
}

/* ================================================= */
/* TOP CONTRIBUTION GRAPH */
/* ================================================= */

function ContributionRow({
  label,
  sublabel,
  value,
  width,
  color,
  theme,
}: {
  label: string
  sublabel: string
  value: number
  width: number
  color: string
  theme: any
}) {
  const positive = value >= 0

  const formatted =
    `${positive ? "+" : "−"}${(
      Math.abs(value) / 1000
    ).toFixed(1)}K`

  return (
    <div className="grid grid-cols-[110px_1fr] items-center gap-3">
      <div>
        <p
          className="text-[14px] font-semibold uppercase tracking-[0.07em]"
          style={{ color: theme.brown }}
        >
          {label}
        </p>

        <p
          className="mt-1 text-[10px]"
          style={{ color: theme.muted }}
        >
          {sublabel}
        </p>
      </div>

      <div className="relative h-8">
        <div
          className="absolute left-1/2 top-0 h-full w-px"
          style={{
            backgroundColor: "#CEC7BD",
          }}
        />

        <div
          className={`absolute top-1/2 flex h-5 -translate-y-1/2 items-center ${
            positive
              ? "left-1/2 justify-end rounded-r-[2px] pr-2"
              : "right-1/2 justify-start rounded-l-[2px] pl-2"
          }`}
          style={{
            width: `${Math.max(width, 8)}%`,
            backgroundColor: color,
          }}
        >
          <span className="whitespace-nowrap text-[10px] font-semibold text-white">
            {formatted}
          </span>
        </div>
      </div>
    </div>
  )
}

/* ================================================= */
/* NEW DISTRIBUTION BAR */
/* ================================================= */

function EntityBar({
  label,
  value,
  width,
  color,
  theme,
}: {
  label: string
  value: string
  width: number
  color: string
  theme: any
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-5">
        <p
          className="text-[12px] font-medium"
          style={{ color: theme.charcoal }}
        >
          {label}
        </p>

        <p
          className="text-[13px] font-semibold"
          style={{ color }}
        >
          {value}
        </p>
      </div>

      <div
        className="mt-2 h-2 overflow-hidden rounded-[2px]"
        style={{
          backgroundColor: theme.track,
        }}
      >
        <div
          className="h-full rounded-[2px]"
          style={{
            width: `${width}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  )
}

/* ================================================= */
/* BIG METRIC */
/* ================================================= */

function BigMetric({
  value,
  label,
  theme,
}: {
  value: string
  label: string
  theme: any
}) {
  return (
    <div
      className="border-l-[3px] pl-4"
      style={{
        borderColor: "#D5D0C9",
      }}
    >
      <p
        className="text-[30px] font-semibold tracking-[-0.04em]"
        style={{ color: theme.charcoal }}
      >
        {value}
      </p>

      <p
        className="mt-1 text-[10px] font-medium uppercase tracking-[0.12em]"
        style={{ color: theme.muted }}
      >
        {label}
      </p>
    </div>
  )
}

/* ================================================= */
/* MATURE ENTITY BAR */
/* ================================================= */

function DualMetricBar({
  label,
  impact,
  metric,
  width,
  negative = false,
  theme,
}: {
  label: string
  impact: string
  metric: string
  width: number
  negative?: boolean
  theme: any
}) {
  const color = negative
    ? theme.red
    : theme.blue

  return (
    <div>
      <div className="grid grid-cols-[1fr_auto_auto] items-center gap-5">
        <p
          className="text-[12px] font-medium"
          style={{ color: theme.charcoal }}
        >
          {label}
        </p>

        <p
          className="text-[11px]"
          style={{ color: theme.muted }}
        >
          {metric}
        </p>

        <p
          className="min-w-[56px] text-right text-[13px] font-semibold"
          style={{ color }}
        >
          {impact}
        </p>
      </div>

      <div
        className="mt-2 h-2 overflow-hidden rounded-[2px]"
        style={{
          backgroundColor: theme.track,
        }}
      >
        <div
          className="h-full rounded-[2px]"
          style={{
            width: `${width}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  )
}