"use client"

import { useEffect, useMemo, useState } from "react"
import { AlertTriangle, ArrowUpRight, Info, X } from "lucide-react"

type Intervention = {
  reaches_oos: boolean | null
  first_oos_date: string | null
  current_po_receipt_date: string | null
  expected_delivery_date: string | null
}

type InventorySku = {
  sku: string
  product_name: string
  inventory_status: string | null
  inventory_urgency: string | null
  has_active_po: boolean | null
  interventions: Intervention[]
}

type InventoryOverview = {
  as_of_date?: string | null
  distribution_centers: Array<{
    distributor: string
    dc: string
    skus: InventorySku[]
  }>
}

type Risk = InventorySku & {
  distributor: string
  dc: string
  oosDate: string | null
  poReceiptDate: string | null
  isOos: boolean
  noActivePo: boolean
  poAfterOos: boolean
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000"

function dateOnly(value: string | null | undefined) {
  return value?.slice(0, 10) ?? null
}

function formatDate(value: string | null) {
  if (!value) return null
  const date = new Date(`${value}T12:00:00`)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

function buildRisks(data: InventoryOverview): Risk[] {
  const today = new Date()
  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`

  return (data.distribution_centers ?? [])
    .flatMap((dc) =>
      (dc.skus ?? [])
        .filter(
          (sku) =>
            sku.inventory_status === "action" &&
            sku.inventory_urgency === "critical"
        )
        .map((sku): Risk => {
          const oosDate = (sku.interventions ?? [])
            .filter((i) => i.reaches_oos === true && i.first_oos_date)
            .map((i) => dateOnly(i.first_oos_date)!)
            .sort()[0] ?? null

          // Receipt timing is provided by the existing assessment; never infer it.
          const poReceiptDate = (sku.interventions ?? [])
            .map((i) => dateOnly(i.current_po_receipt_date))
            .filter((d): d is string => d !== null)
            .sort()[0] ?? null

          return {
            ...sku,
            distributor: dc.distributor,
            dc: dc.dc,
            oosDate,
            poReceiptDate,
            isOos: oosDate !== null && oosDate <= todayKey,
            noActivePo: sku.has_active_po === false,
            poAfterOos:
              oosDate !== null &&
              poReceiptDate !== null &&
              poReceiptDate > oosDate,
          }
        })
    )
    .sort((a, b) => {
      if (a.isOos !== b.isOos) return a.isOos ? -1 : 1
      if (a.oosDate !== b.oosDate) return (a.oosDate ?? "9999").localeCompare(b.oosDate ?? "9999")
      return `${a.distributor}-${a.dc}-${a.sku}`.localeCompare(`${b.distributor}-${b.dc}-${b.sku}`)
    })
}

export default function InventoryRiskPopover({ orgId }: { orgId: string | null | undefined }) {
  const [open, setOpen] = useState(false)
  const [data, setData] = useState<InventoryOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!orgId) {
      setData(null)
      setError(null)
      return
    }

    const controller = new AbortController()
    setData(null)
    setLoading(true)
    setError(null)

    fetch(`${API_BASE_URL}/inventory/overview?${new URLSearchParams({ org_id: orgId })}`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Inventory alerts unavailable (${response.status})`)
        return (await response.json()) as InventoryOverview
      })
      .then(setData)
      .catch((err) => {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Unable to load alerts")
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [orgId])

  const risks = useMemo(() => (data ? buildRisks(data) : []), [data])
  if (!orgId) return null

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {open && (
        <section
          role="dialog"
          aria-label="Critical inventory risks"
          className="flex max-h-[min(650px,75vh)] w-[min(420px,calc(100vw-32px))] flex-col overflow-hidden rounded-[22px] border border-[#E5DDD0] bg-[#FFFDF9] shadow-2xl"
        >
          <div className="flex items-start justify-between gap-4 border-b border-[#EEE5D8] px-5 py-4">
            <div>
              <div className="flex items-center gap-2 text-[15px] font-semibold text-[#343332]">
                <AlertTriangle className="h-4 w-4 text-[#B84D34]" />
                Critical inventory risks
                {!loading && !error && (
                  <span className="rounded-full bg-[#FFF2EE] px-2 py-0.5 text-xs text-[#B84D34]">{risks.length}</span>
                )}
              </div>
              <p className="mt-1 text-xs text-[#8A8179]">Projected risks · refreshed from inventory planning</p>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close inventory risks" className="rounded-lg p-1.5 text-[#705C4F] hover:bg-[#F6F2EA]">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex items-start gap-2 border-b border-[#EEE5D8] bg-[#F6F2EA] px-5 py-3 text-xs leading-5 text-[#705C4F]">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <p>These alerts estimate current inventory using the latest distributor data, sales velocity, and expected PO arrivals. Figures may differ from the reported inventory shown on this page.</p>
          </div>

          <div className="overflow-y-auto">
            {loading && <p className="px-5 py-6 text-sm text-[#705C4F]">Loading projected risks…</p>}
            {error && <p className="px-5 py-6 text-sm text-[#B84D34]">{error}</p>}
            {!loading && !error && risks.length === 0 && (
              <p className="px-5 py-6 text-sm text-[#705C4F]">No critical inventory risks currently identified.</p>
            )}
            {!loading && !error && risks.map((risk) => (
              <div key={`${risk.distributor}:${risk.dc}:${risk.sku}`} className="border-b border-[#EEE5D8] px-5 py-3.5 last:border-b-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.11em] text-[#8A8179]">{risk.distributor} · {risk.dc}</p>
                    <p className="mt-1 truncate text-sm font-semibold text-[#343332]">{risk.product_name || risk.sku}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className={`text-xs font-semibold ${risk.isOos ? "text-[#B84D34]" : "text-[#343332]"}`}>
                      {risk.isOos ? "Projected OOS now" : risk.oosDate ? `OOS ${formatDate(risk.oosDate)}` : "Critical risk"}
                    </p>
                    {risk.noActivePo && <p className="mt-1 text-[11px] text-[#B84D34]">No active PO</p>}
                    {!risk.noActivePo && risk.poAfterOos && <p className="mt-1 text-[11px] text-[#B84D34]">PO expected {formatDate(risk.poReceiptDate)} · after OOS</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <a href="/inventory" className="flex items-center justify-center gap-1.5 border-t border-[#EEE5D8] px-5 py-3.5 text-xs font-semibold text-[#705C4F] hover:bg-[#FCFAF6]">
            Open inventory planning <ArrowUpRight className="h-3.5 w-3.5" />
          </a>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label="Show projected inventory risks"
        className="flex items-center gap-2 rounded-full border border-[#E7C0B6] bg-[#FFF2EE] px-4 py-3 text-sm font-semibold text-[#B84D34] shadow-lg transition hover:bg-[#FBE8E1]"
      >
        <AlertTriangle className="h-4 w-4" />
        {loading ? "Loading risks" : error ? "Risks unavailable" : `${risks.length} projected ${risks.length === 1 ? "risk" : "risks"}`}
      </button>
    </div>
  )
}