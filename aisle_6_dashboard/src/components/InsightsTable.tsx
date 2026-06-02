"use client"

import { useState, useEffect } from "react"
import { useOrg } from "@/components/OrgContext"
import { supabase } from "@/lib/supabase"

type Column = {
  key: string
  label: string
  align?: "left" | "right" | "center"
  format?: "number" | "currency" | "decimal" | "month" | "status" | "sku_pills" | "percent"
  width?: string
}

type InsightTableProps = {
  data?: {
    title?: string
    subtitle?: string
    columns?: Column[]
    rows?: Record<string, any>[]
    result?: Record<string, any>[]
    table_width?: string
  }
}

type SortDirection = "asc" | "desc"

function downloadCSV(columns: Column[], rows: Record<string, any>[], filename = "insight_table") {
  const headers = columns.map((col) => col.label)

  const csvRows = rows.map((row) =>
    columns.map((col) => {
      const value = row[col.key]
      if (value == null) return ""

      return `"${String(value).replace(/"/g, '""')}"`
    })
  )

  const csv = [headers, ...csvRows]
    .map((row) => row.join(","))
    .join("\n")

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)

  const link = document.createElement("a")
  link.href = url
  link.download = `${filename}.csv`
  link.click()

  URL.revokeObjectURL(url)
}

export default function InsightTable({ data }: InsightTableProps) {
  const { org } = useOrg()

  const [sortKey, setSortKey] = useState<string>("")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")
  const [skuColorMap, setSkuColorMap] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!org?.id) return

    async function loadSkuColors() {
      const { data, error } = await supabase
        .from("sku_display_colors")
        .select("sku_name, color")
        .eq("org_id", org.id)

      if (error) {
        console.error("Error loading SKU colors:", error)
        return
      }

      const colorMap = Object.fromEntries(
        (data ?? []).map((row) => [row.sku_name, row.color])
      )

      setSkuColorMap(colorMap)
    }

    loadSkuColors()
  }, [org?.id])  

  if (!data) return null

  const columns = data.columns ?? []
  const rows = Array.isArray(data.rows)
    ? data.rows
    : Array.isArray(data.result)
    ? data.result
    : []

  const activeSortKey =
    sortKey ||
    columns.find((col) => col.key === "units")?.key ||
    columns.find((col) => col.key === "brand_units")?.key ||
    columns[0]?.key ||
    ""

  function handleSort(column: string) {
    if (activeSortKey === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortKey(column)
      setSortDirection("desc")
    }
  }

  const sortedRows = [...rows].sort((a, b) => {
    if (!activeSortKey) return 0

    const aVal = a[activeSortKey]
    const bVal = b[activeSortKey]

    if (aVal == null && bVal == null) return 0
    if (aVal == null) return 1
    if (bVal == null) return -1

    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortDirection === "asc" ? aVal - bVal : bVal - aVal
    }

    return sortDirection === "asc"
      ? String(aVal).localeCompare(String(bVal))
      : String(bVal).localeCompare(String(aVal))
  })

  const filename =
    data.title
      ?.toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "") || "insight_table"

  if (!columns.length) {
    return (
      <div className="mt-6 rounded-[20px] border border-black/10 bg-white p-6 text-sm text-neutral-500">
        No rows found.
      </div>
    )
  }

  return (
    <div className="mt-6">
      <div className="mb-3 flex justify-end">
        <button
          type="button"
          onClick={() => downloadCSV(columns, sortedRows, filename)}
          className="rounded-full border border-black/10 bg-white px-4 py-2 text-sm font-medium text-neutral-700 shadow-sm hover:bg-black/[0.03]"
        >
          Download CSV
        </button>
      </div>

      <div
  className={`mx-auto overflow-hidden rounded-[20px] border border-black/10 bg-white ${data.table_width ?? ""}`}>
        <div className="max-h-[420px] overflow-auto">
          <table className="w-full text-sm">
            <thead
              className="sticky top-0 z-10"
              style={{ backgroundColor: org?.primary_color ?? "#92B9DC" }}
            >
              <tr className="[&_th]:px-4 [&_th]:py-3 [&_th]:text-[11px] [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-[0.14em] [&_th]:text-white">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    style={{ width: col.width }}
                    className={`cursor-pointer ${
                      col.align === "right"
                        ? "text-right"
                        : col.align === "center"
                        ? "text-center"
                        : "text-left"
                    } ${col.format === "sku_pills" ? "w-[170px] align-top" : ""}`}
                  >
                    {col.label}
                    {activeSortKey === col.key && (
                      <span className="ml-1">
                        {sortDirection === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {sortedRows.length > 0 ? (
                sortedRows.map((row, index) => (
                  <tr
                    key={`${row.coded_customer ?? "row"}-${index}`}
                    className="border-b border-black/5"
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        style={{ width: col.width }}
                        className={`px-4 py-3 ${
                          col.key === "coded_customer"
                            ? "font-medium text-neutral-900"
                            : "text-neutral-700"
                        } ${
                          col.align === "right"
                            ? "text-right"
                            : col.align === "center"
                            ? "text-center"
                            : "text-left"
                        } ${col.format === "sku_pills" ? "w-[170px] align-top" : ""}`}
                      >
                        {formatCell(row[col.key], col.format, skuColorMap)}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-4 py-10 text-center text-sm text-neutral-500"
                  >
                    No rows found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function formatCell(
    value: any,
    format?: string,
    skuColorMap?: Record<string, string>
  ) {
    if (value == null || value === "") return "—"

    if (format === "sku_pills") {
      const skus = Array.isArray(value)
        ? value
        : String(value).split(",").map((sku) => sku.trim()).filter(Boolean)

      return (
        <div className="flex min-w-[150px] flex-col gap-1.5">
          {skus.map((sku) => {
            const color = skuColorMap?.[sku] ?? "#705C4F"

            return (
              <span
                key={sku}
                className="inline-flex w-fit max-w-[150px] items-center rounded-full px-2 py-0.5 text-[11px] font-medium leading-tight"
                style={{
                  backgroundColor: `${color}20`,
                  color,
                  border: `1px solid ${color}40`,
                }}
              >
                {sku}
              </span>
            )
          })}
        </div>
      )
    }

    if (format === "number") return Number(value).toLocaleString()

    if (format === "percent") {return `${(Number(value) * 100).toFixed(1)}%`}

    if (format === "currency") {
      return `$${Number(value).toLocaleString(undefined, {
        maximumFractionDigits: 0,
      })}`
    }

    if (format === "decimal") return Number(value).toFixed(1)

    if (format === "month") return String(value)

    if (format === "status") return <StatusPill status={String(value)} />

    return String(value)
  }

function StatusPill({ status }: { status: string }) {
  const tone =
    status === "Healthy"
      ? "bg-[#EAF3DE] text-[#3B6D11]"
      : status === "Struggling"
      ? "bg-[#FBF1EF] text-[#A06057]"
      : status === "Revived"
      ? "bg-[#EEF4F8] text-[#343332]"
      : status === "New"
      ? "bg-[#FFF4D8] text-[#8A5A00]"
      : "bg-neutral-100 text-neutral-600"

  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${tone}`}>
      {status}
    </span>
  )
}