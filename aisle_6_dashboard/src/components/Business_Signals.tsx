"use client"

type Signal = {
  signal_type: string
  direction: "positive" | "negative" | "neutral"
  scope_type: string

  scope: {
    chain?: string
    state?: string
    sku?: string
  }

  metrics: Record<string, number | null>

  benchmark?: {
    type?: string
    vpo_3m?: number
  } | null

  scale: {
    revenue_3m?: number
    units_3m?: number
    buying_stores_3m?: number
    vpo_3m?: number
  }

  strength: number
}

type Props = {
  signals: Signal[]
}

function formatScope(signal: Signal) {
  const parts = []

  if (signal.scope.chain) {
    parts.push(signal.scope.chain)
  }

  if (signal.scope.state) {
    parts.push(signal.scope.state)
  }

  if (signal.scope.sku) {
    parts.push(signal.scope.sku)
  }

  if (parts.length === 0) {
    return "Overall Business"
  }

  return parts.join(" · ")
}

function formatSignalType(signalType: string) {
  const labels: Record<string, string> = {
    revenue_growth: "Revenue Growth",
    revenue_decline: "Revenue Decline",

    unit_growth: "Unit Growth",
    unit_decline: "Unit Decline",

    distribution_expansion: "Distribution Expansion",
    distribution_contraction: "Distribution Contraction",

    velocity_growth: "Velocity Growth",
    velocity_pressure: "Velocity Pressure",

    growth_with_velocity: "Growth + Velocity",
    growth_with_velocity_pressure:
      "Growth With Velocity Pressure",

    velocity_outperformance:
      "Velocity Outperformance",

    velocity_underperformance:
      "Velocity Underperformance",
  }

  return labels[signalType] ?? signalType
}

function formatMetric(
  key: string,
  value: number | null
) {
  if (value === null || value === undefined) {
    return "—"
  }

  if (key.includes("_pct")) {
    return `${value >= 0 ? "+" : ""}${(
      value * 100
    ).toFixed(1)}%`
  }

  if (key.includes("revenue")) {
    return value.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    })
  }

  if (key.includes("vpo")) {
    return value.toFixed(2)
  }

  return value.toLocaleString()
}

function formatMetricName(key: string) {
  const labels: Record<string, string> = {
    revenue_l3m_pct: "Revenue",
    units_l3m_pct: "Units",
    buying_stores_l3m_pct: "Buying Stores",
    vpo_l3m_pct: "VPO",
    vpo_difference_pct: "Vs. Benchmark",
    vpo_3m: "VPO",
  }

  return labels[key] ?? key
}

export default function BusinessSignals({
  signals,
}: Props) {
  if (!signals?.length) {
    return (
      <div className="rounded-2xl border bg-white p-5">
        <p className="text-sm text-neutral-500">
          No meaningful signals detected.
        </p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      {signals.map((signal, index) => (
        <div
          key={index}
          className="rounded-2xl border bg-white p-5 shadow-sm"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-1 text-xs font-semibold ${
                    signal.direction === "positive"
                      ? "bg-green-100 text-green-700"
                      : signal.direction === "negative"
                      ? "bg-red-100 text-red-700"
                      : "bg-neutral-100 text-neutral-600"
                  }`}
                >
                  {signal.direction.toUpperCase()}
                </span>

                <span className="text-xs font-medium uppercase tracking-wide text-neutral-400">
                  {signal.scope_type.replaceAll("_", " ")}
                </span>
              </div>

              <h3 className="text-base font-semibold text-neutral-900">
                {formatSignalType(
                  signal.signal_type
                )}
              </h3>

              <p className="mt-1 text-sm text-neutral-500">
                {formatScope(signal)}
              </p>
            </div>

            <div className="text-right">
              <div className="text-lg font-semibold text-neutral-900">
                {signal.strength.toFixed(2)}
              </div>

              <div className="text-xs uppercase tracking-wide text-neutral-400">
                Strength
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {Object.entries(signal.metrics).map(
              ([key, value]) => {
                if (
                  value === null ||
                  value === undefined
                ) {
                  return null
                }

                return (
                  <div
                    key={key}
                    className="rounded-xl bg-neutral-50 px-3 py-2"
                  >
                    <div className="text-xs text-neutral-400">
                      {formatMetricName(key)}
                    </div>

                    <div className="text-sm font-semibold text-neutral-800">
                      {formatMetric(key, value)}
                    </div>
                  </div>
                )
              }
            )}
          </div>

          {signal.scale.buying_stores_3m !==
            undefined && (
            <p className="mt-3 text-xs text-neutral-400">
              Based on{" "}
              {signal.scale.buying_stores_3m.toLocaleString()}{" "}
              buying stores
            </p>
          )}
        </div>
      ))}
    </div>
  )
}