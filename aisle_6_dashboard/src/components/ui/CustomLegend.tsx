type LegendRow = {
  name: string
  value: number
}

function normalizeLegendData(data: LegendRow[]) {
  return (Array.isArray(data) ? data : [])
    .filter(
      (item) =>
        item &&
        typeof item.name === "string" &&
        typeof item.value === "number" &&
        !Number.isNaN(item.value) &&
        item.value > 0
    )
    .sort((a, b) => b.value - a.value)
}

function groupLegendData(data: LegendRow[]) {
  const normalized = normalizeLegendData(data)

  if (normalized.length <= 10) return normalized

  const top = normalized.slice(0, 6)
  const rest = normalized.slice(6)

  const otherValue = rest.reduce((sum, item) => sum + item.value, 0)

  return [
    ...top,
    {
      name: "Other",
      value: otherValue,
    },
  ]
}

export default function CustomLegend({
  data,
  colorMap,
}: {
  data: LegendRow[]
  colorMap: Record<string, string>
}) {
  const legendData = groupLegendData(data)
  const total = legendData.reduce((sum, item) => sum + item.value, 0)

  const isDense = legendData.length > 6

  return (
    <div
      className={
        isDense
          ? "grid w-full max-w-[240px] grid-cols-2 gap-x-2 gap-y-2"
          : "flex w-full max-w-[220px] flex-col gap-2"
      }
    >
      {legendData.map((item) => {
        const pct = total > 0 ? (item.value / total) * 100 : 0
        const fill =
          item.name === "Other"
            ? "#D6D3D1"
            : colorMap[item.name] || "#D1D5DB"

        return (
          <div
            key={item.name}
            className="flex items-center justify-between rounded-full border px-3 py-2"
            style={{ borderColor: "#E6DCD2", backgroundColor: "#FFFEFB" }}
          >
            <div className="flex min-w-0 items-center gap-2">
              <div
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: fill }}
              />
              <span className="truncate text-[11px] uppercase tracking-[0.08em] text-[#6F6257]">
                {item.name}
              </span>
            </div>

            <span className="ml-2 shrink-0 text-[11px] font-medium text-[#7A746B]">
              {pct.toFixed(0)}%
            </span>
          </div>
        )
      })}
    </div>
  )
}