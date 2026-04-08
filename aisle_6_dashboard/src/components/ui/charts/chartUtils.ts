
/* formatting helpers */

export function formatMonth(month: string) {
  const [year, monthNum] = month.split("-")
  const date = new Date(Number(year), Number(monthNum) - 1)

  return date.toLocaleString("en-US", {
    month: "short",
    year: "numeric",
  })
}

export function formatWholeNumber(value: number) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatPercent(value: number) {
  const pct = Math.abs(value * 100)

  if (pct >= 1000) {
    const short = pct / 1000
    return short >= 10 ? `${Math.round(short)}K` : `${short.toFixed(1)}K`
  }

  return Math.round(pct).toString()
}

export function formatNumber(value: unknown) {
  const num = Number(value)

  if (Number.isNaN(num)) return ""

  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M"
  if (num >= 1000) return (num / 1000).toFixed(1) + "K"
  if (num < 5) return num.toFixed(1)

  return num.toString()
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