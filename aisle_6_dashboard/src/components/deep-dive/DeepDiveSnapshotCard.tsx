"use client"

type Theme = {
  surface: string
  line: string
  accent_color: string
  charcoal: string
}

type TrendDirection = "up" | "down" | "flat"

type DeepDiveSnapshotCardProps = {
  label: string
  value: string
  unit?: string
  trendValue?: string
  trendLabel?: string
  trendDirection?: TrendDirection
  interpretation: string
  accentColor: string | null
  theme: Theme
  isExpanded?: boolean
  onToggle?: () => void
  expandedPoints?: string[]
}

function TrendIcon({ direction }: { direction: TrendDirection }) {
  if (direction === "up") {
    return (
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
        <path
          d="M2 8L8 2M8 2H3.8M8 2V6.2"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    )
  }

  if (direction === "down") {
    return (
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
        <path
          d="M2 2L8 8M8 8H3.8M8 8V3.8"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    )
  }

  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
      <path
        d="M2 5H8"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  )
}

function getTrendStyles(direction: TrendDirection) {
  if (direction === "up") {
    return {
      bg: "#EAF3DE",
      text: "#3B6D11",
    }
  }

  if (direction === "down") {
    return {
      bg: "#FBF1EF",
      text: "#A06057",
    }
  }

  return {
    bg: "#FFF4D8",
    text: "#8A6A12",
  }
}

export default function DeepDiveSnapshotCard({
  label,
  value,
  unit,
  trendValue,
  trendLabel,
  trendDirection = "flat",
  interpretation,
  accentColor,
  theme,
  isExpanded = false,
  onToggle,
  expandedPoints = [],
}: DeepDiveSnapshotCardProps) {
  const trendStyles = getTrendStyles(trendDirection)

  const pointsToShow =
    expandedPoints.length > 0
      ? expandedPoints
      : [
          "Whole Foods accounted for 42% of the increase.",
          "SKU D added 31 new active stores.",
          "Natural channel velocity improved 18%.",
        ]

  return (
    <div
      onClick={onToggle}
      className="relative cursor-pointer rounded-[28px] border px-5 py-5 shadow-sm transition-all hover:shadow-md"
      style={{
        backgroundColor: theme.surface,
        borderColor: isExpanded ? accentColor ?? theme.line : theme.line,
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="h-[3px] w-16 rounded-full"
          style={{ backgroundColor: `${accentColor}CC` }}
        />

        <p
          className="text-[13px] font-medium uppercase tracking-[0.18em]"
          style={{ color: "#6B6B6B" }}
        >
          {label}
        </p>
      </div>

      <div className="mt-6 flex items-end gap-2">
        <div
          className="text-[34px] font-semibold leading-none tracking-[-0.04em]"
          style={{ color: theme.charcoal }}
        >
          {value}
        </div>

        {unit && (
          <div
            className="pb-1.5 text-[14px] font-medium"
            style={{ color: theme.accent_color }}
          >
            {unit}
          </div>
        )}
      </div>

      {trendValue && (
        <div className="mt-4 flex items-center gap-2">
          <div
            className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-[12px] font-medium"
            style={{
              backgroundColor: trendStyles.bg,
              color: trendStyles.text,
            }}
          >
            <span className="flex h-3 w-3 items-center justify-center">
              <TrendIcon direction={trendDirection} />
            </span>

            <span>{trendValue}</span>
          </div>

          {trendLabel && (
            <span
              className="text-[11px] uppercase tracking-[0.12em]"
              style={{ color: theme.accent_color, opacity: 0.72 }}
            >
              {trendLabel}
            </span>
          )}
        </div>
      )}

      <div
        className="mt-5 border-t pt-4"
        style={{ borderColor: theme.line }}
      >
        <p
          className="text-[14px] leading-6"
          style={{ color: theme.charcoal }}
        >
          {interpretation}
        </p>
      </div>

      {isExpanded && (
        <div
          className="absolute left-5 right-5 top-[calc(100%-24px)] z-20 rounded-2xl border px-4 py-4 shadow-lg"
          style={{
            backgroundColor: "#FFFEFB",
            borderColor: theme.line,
          }}
        >
          <p
            className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: "#9A8A7C" }}
          >
            What’s driving this
          </p>

          <ul
            className="space-y-2 text-[14px] leading-relaxed"
            style={{ color: "#705C4F" }}
          >
            {pointsToShow.map((point, index) => (
              <li key={index}>• {point}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}