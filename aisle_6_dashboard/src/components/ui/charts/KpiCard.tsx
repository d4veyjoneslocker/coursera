"use client"

import { formatPercent } from "./chartUtils"

type KpiCardProps = {
  title: string
  value: string
  sideLabel?: string
  sideValue?: number
  sideType?: "percent" | "absolute"
  theme: {
    accent_color: string
    charcoal: string
  }
}

export default function KpiCard({
  title,
  value,
  sideLabel,
  sideValue,
  sideType = "percent",
  theme,
}: KpiCardProps) {
  const isPositive = sideValue !== undefined && sideValue > 0
  const isNegative = sideValue !== undefined && sideValue < 0

  const chipStyles =
    isPositive
      ? {
          bg: "#EAF3DE",
          text: "#3B6D11",
        }
      : isNegative
      ? {
          bg: "#FBF1EF",
          text: "#A06057",
        }
      : {
          bg: "#F4F1EC",
          text: "#705C4F",
        }

  return (
    <div
      className="rounded-[22px] border px-3.5 pt-2 pb-3.5"
      style={{
        backgroundColor: "#FCFAF6",
        borderColor: "#EEE5D8",
      }}
    >
      <div className="mt-2">
        <div className="min-w-0">
          <p
            className="text-xs uppercase tracking-[0.12em] leading-tight"
            style={{ color: theme.accent_color }}
          >
            {title}
          </p>
        </div>

        <div className="mt-1 flex justify-between gap-4">
          <div className="flex min-w-0 items-end">
            <div
              className="text-[32px] font-semibold leading-none tracking-[-0.03em]"
              style={{ color: theme.charcoal }}
            >
              {value}
            </div>
          </div>

          <div className="flex min-h-[42px] flex-col items-end justify-end gap-1">
            {sideValue !== undefined && (
              <>
                <div
                  className="inline-flex items-center gap-1 rounded-full px-2.5 py-[3px] text-[12px] font-medium ml-[-10px]"                  
                  style={{
                    backgroundColor: chipStyles.bg,
                    color: chipStyles.text,
                  }}
                >
                  {/* Arrow (no background) */}
                  <span className="flex h-3 w-3 items-center justify-center">
                    {isPositive ? (
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path
                          d="M2 8L8 2M8 2H3.8M8 2V6.2"
                          stroke="currentColor"
                          strokeWidth="1.2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    ) : isNegative ? (
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path
                          d="M2 2L8 8M8 8H3.8M8 8V3.8"
                          stroke="currentColor"
                          strokeWidth="1.2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    ) : (
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path
                          d="M2 5H8"
                          stroke="currentColor"
                          strokeWidth="1.2"
                          strokeLinecap="round"
                        />
                      </svg>
                    )}
                  </span>

                  {/* Value */}
                  <span>
                    {sideType === "absolute"
                      ? `${isPositive ? "+" : isNegative ? "-" : ""}${formatPercent(Math.abs(sideValue))}`
                      : `${formatPercent(sideValue)}%`}
                  </span>
                </div>

                {sideLabel && (
                  <span
                    className="pr-[3px] text-[10px] uppercase tracking-[0.12em]"
                    style={{ color: theme.accent_color, opacity: 0.72 }}
                  >
                    {sideLabel}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}