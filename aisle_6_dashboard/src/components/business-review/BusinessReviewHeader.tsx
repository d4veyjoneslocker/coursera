"use client"

import { FileText } from "lucide-react"
import { useOrg } from "@/components/OrgContext"

export type ReviewPeriod = "H1" | "H2" | "FY"
export type ReviewComparison = "PY" | "PP"

type BusinessReviewHeaderProps = {
  period: ReviewPeriod
  year: number
  comparison: ReviewComparison
  years: number[]
  headline: string
  summary: string
  comparisonLabel: string
  onPeriodChange: (period: ReviewPeriod) => void
  onYearChange: (year: number) => void
  onComparisonChange: (comparison: ReviewComparison) => void
}

const DEFAULT_THEME = {
  primary_color: "#9A93B0",
  secondary_color: "#C58E82",
  accent_color: "#C8795A",
  charcoal: "#343332",
  line: "#E5DDD0",
  muted: "#7A746B",
  controlBg: "#F1ECE2",
}

export default function BusinessReviewHeader({
  period,
  year,
  comparison,
  years,
  headline,
  summary,
  comparisonLabel,
  onPeriodChange,
  onYearChange,
  onComparisonChange,
}: BusinessReviewHeaderProps) {
  const { org } = useOrg()

  const theme = {
    ...DEFAULT_THEME,
    primary_color: org?.primary_color || DEFAULT_THEME.primary_color,
    secondary_color: org?.secondary_color || DEFAULT_THEME.secondary_color,
    accent_color: org?.accent_color || DEFAULT_THEME.accent_color,
  }

  return (
    <header>
      {/* app-style header row */}
      <div
        className="flex min-h-[94px] flex-col gap-5 border-b py-5 lg:flex-row lg:items-center lg:justify-between"
        style={{ borderColor: theme.line }}
      >
        <div className="flex min-w-0 items-center gap-4">
          {org && (
            <div className="flex shrink-0 items-center">
              {org.logo_display === "both" &&
              org.logo_mark_url &&
              org.logo_wordmark_url ? (
                <div className="flex items-center gap-2.5">
                  <img
                    src={org.logo_mark_url}
                    alt=""
                    className="h-[34px] w-auto object-contain"
                  />
                  <img
                    src={org.logo_wordmark_url}
                    alt={org.name}
                    className="h-[30px] w-auto max-w-[170px] object-contain"
                  />
                </div>
              ) : org.logo_display === "mark" && org.logo_mark_url ? (
                <img
                  src={org.logo_mark_url}
                  alt={org.name}
                  className="h-[36px] w-auto object-contain"
                />
              ) : org.logo_display === "wordmark" && org.logo_wordmark_url ? (
                <img
                  src={org.logo_wordmark_url}
                  alt={org.name}
                  className="h-[30px] w-auto max-w-[190px] object-contain"
                />
              ) : (
                <span
                  className="truncate text-[20px] font-semibold tracking-[-0.02em]"
                  style={{ color: theme.charcoal }}
                >
                  {org.name}
                </span>
              )}
            </div>
          )}

          {org && (
            <div
              className="hidden h-8 w-px sm:block"
              style={{ backgroundColor: theme.line }}
            />
          )}

          <div className="min-w-0">
            <div
              className="text-[15px] font-semibold"
              style={{ color: theme.charcoal }}
            >
              Business Review
            </div>
            <div
              className="mt-0.5 text-[12px]"
              style={{ color: theme.muted }}
            >
              Executive performance summary
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <SegmentedControl
            options={[
              ["H1", "H1"],
              ["H2", "H2"],
              ["FY", "FY"],
            ]}
            value={period}
            onChange={(value) => onPeriodChange(value as ReviewPeriod)}
            theme={theme}
          />

          <SegmentedControl
            options={years.map((item) => [String(item), String(item)])}
            value={String(year)}
            onChange={(value) => onYearChange(Number(value))}
            theme={theme}
          />

          <SegmentedControl
            options={[
              ["PY", "vs Prior Year"],
              ["PP", "vs Prior Period"],
            ]}
            value={comparison}
            onChange={(value) =>
              onComparisonChange(value as ReviewComparison)
            }
            theme={theme}
          />
        </div>
      </div>

      {/* editorial report intro */}
      <div className="mx-auto max-w-5xl py-10 lg:py-14">
        <div
          className="mb-5 flex items-center gap-2 text-[12px] font-medium"
          style={{ color: theme.muted }}
        >
          <FileText
            className="h-4 w-4"
            strokeWidth={1.8}
            style={{ color: theme.primary_color }}
          />
          <span>
            {period} {year}
          </span>
          <span style={{ color: theme.line }}>•</span>
          <span>Compared with {comparisonLabel}</span>
        </div>

        <h1
          className="max-w-4xl text-4xl font-semibold leading-[1.04] tracking-[-0.045em] sm:text-5xl lg:text-6xl"
          style={{ color: theme.charcoal }}
        >
          {headline}
        </h1>

        <p
          className="mt-6 max-w-3xl text-[17px] leading-8"
          style={{ color: theme.muted }}
        >
          {summary}
        </p>
      </div>
    </header>
  )
}

function SegmentedControl({
  options,
  value,
  onChange,
  theme,
}: {
  options: [string, string][]
  value: string
  onChange: (value: string) => void
  theme: typeof DEFAULT_THEME
}) {
  return (
    <div
      className="flex items-center rounded-[18px] border p-1"
      style={{
        borderColor: "#DED4C4",
        backgroundColor: "#FBF8F2",
      }}
    >
      {options.map(([optionValue, label]) => {
        const active = value === optionValue

        return (
          <button
            key={optionValue}
            type="button"
            onClick={() => onChange(optionValue)}
            className="h-[40px] rounded-[13px] px-4 text-[13px] font-medium transition-all duration-150"
            style={{
              backgroundColor: active ? theme.charcoal : "transparent",
              color: active ? "#FFFFFF" : theme.muted,
              boxShadow: active
                ? "0 1px 3px rgba(52,51,50,0.14)"
                : "none",
            }}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}
