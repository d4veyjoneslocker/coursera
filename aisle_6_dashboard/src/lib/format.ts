export function formatCompact(value: number): string {
  const abs = Math.abs(value)

  if (abs >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`
  }

  if (abs >= 10_000) {
    return `${(value / 1_000).toFixed(0)}K` 
  }

  if (abs >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`
  }

  return Math.round(value).toLocaleString()
}

export function formatWhole(value: number): string {
  return Math.round(value).toLocaleString()
}

export function formatDecimal(
  value: number | null | undefined,
  decimals = 1
): string {
  if (value == null || !Number.isFinite(value)) {
    return "—";
  }

  return value.toFixed(decimals);
}

export function formatPercent(
  value: number,
  decimals = 0
): string {
  return `${(value * 100).toFixed(decimals)}%`
}

export function formatMonth(month: string) {
  const [year, monthNum] = month.split("-")
  const date = new Date(Number(year), Number(monthNum) - 1)

  return date.toLocaleString("en-US", {
    month: "short",
    year: "numeric",
  })
}

export function splitCenterLabel(label: string) {
  const words = label.toUpperCase().split(" ")
  const lines: string[] = []
  let currentLine = ""

  const MAX_CHARS_PER_LINE = 11

  words.forEach((word) => {
    if ((currentLine + " " + word).trim().length > MAX_CHARS_PER_LINE) {
      if (currentLine) lines.push(currentLine)
      currentLine = word
    } else {
      currentLine = currentLine ? `${currentLine} ${word}` : word
    }
  })

  if (currentLine) lines.push(currentLine)

  return lines
}

export const chartConfig = {
  value: {
    label: "Value",
    color: "#3b82f6",
  },
}