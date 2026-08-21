"use client"

type AnalysisRow = Record<string, any>

type BusinessAnalysis = {
  overall?: AnalysisRow[]
  sku?: AnalysisRow[]
  retailer?: AnalysisRow[]
  state?: AnalysisRow[]
  retailer_sku?: AnalysisRow[]
  state_sku?: AnalysisRow[]
}

type BusinessAnalysisViewProps = {
  data: BusinessAnalysis
}

const sectionConfig = [
  {
    key: "overall",
    title: "Overall Business",
  },
  {
    key: "sku",
    title: "By SKU",
  },
  {
    key: "retailer",
    title: "Top Retailers",
  },
  {
    key: "state",
    title: "Top States",
  },
  {
    key: "retailer_sku",
    title: "Retailer × SKU",
  },
  {
    key: "state_sku",
    title: "State × SKU",
  },
] as const

const preferredColumns = [
  "chain",
  "state",
  "sku",
  "revenue_3m",
  "units_3m",
  "buying_stores_3m",
  "vpo_3m",
  "revenue_l3m_pct",
  "units_l3m_pct",
  "buying_stores_l3m_pct",
  "vpo_l3m_pct",
]

function formatColumnName(column: string) {
  const labels: Record<string, string> = {
    chain: "Retailer",
    state: "State",
    sku: "SKU",
    revenue_3m: "L3M Revenue",
    units_3m: "L3M Units",
    buying_stores_3m: "Buying Stores",
    vpo_3m: "VPO",
    revenue_l3m_pct: "Revenue Growth",
    units_l3m_pct: "Unit Growth",
    buying_stores_l3m_pct: "Store Growth",
    vpo_l3m_pct: "VPO Growth",
  }

  return labels[column] ?? column
}

function formatValue(column: string, value: any) {
  if (value === null || value === undefined) {
    return "—"
  }

  if (
    [
      "revenue_l3m_pct",
      "units_l3m_pct",
      "buying_stores_l3m_pct",
      "vpo_l3m_pct",
    ].includes(column)
  ) {
    return `${(Number(value) * 100).toFixed(1)}%`
  }

  if (column === "revenue_3m") {
    return Number(value).toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    })
  }

  if (column === "units_3m" || column === "buying_stores_3m") {
    return Number(value).toLocaleString("en-US", {
      maximumFractionDigits: 0,
    })
  }

  if (column === "vpo_3m") {
    return Number(value).toFixed(2)
  }

  return String(value)
}

function AnalysisTable({
  title,
  rows,
}: {
  title: string
  rows: AnalysisRow[]
}) {
  if (!rows || rows.length === 0) {
    return null
  }

  const columns = preferredColumns.filter((column) =>
    rows.some((row) => column in row)
  )

  return (
    <div className="rounded-2xl border bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-neutral-900">
          {title}
        </h2>

        <p className="text-sm text-neutral-500">
          Latest completed 3-month performance
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              {columns.map((column) => (
                <th
                  key={column}
                  className="whitespace-nowrap px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500"
                >
                  {formatColumnName(column)}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, index) => (
              <tr
                key={index}
                className="border-b last:border-0"
              >
                {columns.map((column) => (
                  <td
                    key={column}
                    className="whitespace-nowrap px-3 py-3 text-neutral-800"
                  >
                    {formatValue(
                      column,
                      row[column]
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function BusinessAnalysisView({
  data,
}: BusinessAnalysisViewProps) {
  return (
    <div className="space-y-6">
      {sectionConfig.map((section) => {
        const rows =
          data[section.key as keyof BusinessAnalysis]

        if (!rows?.length) {
          return null
        }

        return (
          <AnalysisTable
            key={section.key}
            title={section.title}
            rows={rows}
          />
        )
      })}
    </div>
  )
}