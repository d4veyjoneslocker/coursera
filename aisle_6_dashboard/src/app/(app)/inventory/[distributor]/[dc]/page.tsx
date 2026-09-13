"use client"

import { useEffect, useMemo, useState } from "react"
import { useParams } from "next/navigation"
import {
  AlertTriangle,
  ArrowDownToLine,
  Box,
  Building2,
  Clock3,
  MapPin,
  PackageCheck,
  RefreshCw,
  Store,
  TrendingUp,
  Warehouse,
} from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"


const theme = {
  primary: "#9A93B0",
  secondary: "#C58E82",
  accent: "#C8795A",
  charcoal: "#343332",
  brown: "#705C4F",
  cream: "#E9E2C8",
  bg: "#F6F2EA",
  line: "#E5DDD0",
  surface: "#FFFDF9",
  softSurface: "#FCFAF6",
  softLine: "#EEE5D8",
  coral: "#EE6A4C",
  coralDark: "#D9532F",
}


type SkuRow = {
  sku: string
  product_name: string
  image_url: string | null
  units_per_case: number | null
  quantity_on_hand_cases: number | null
  quantity_on_hand_units: number | null
  quantity_on_po_cases: number | null
  quantity_on_po_units: number | null
  units_per_week: number | null
  cases_per_week: number | null
  weeks_on_hand: number | null
  weeks_with_inbound: number | null
  recommended_cases_to_send: number | null
  monitor_inbound: boolean
  order_needed: boolean
  lead_time_risk: boolean
  status: string
}


type StoreRow = {
  coded_customer: string | null
  chain: string | null
  channel: string | null
  state: string | null
}


type DcDetail = {
  distributor: string
  dc: string
  dc_name: string
  status: string

  quantity_on_hand_cases: number | null
  quantity_on_hand_units: number | null

  quantity_on_po_cases: number | null
  quantity_on_po_units: number | null

  weeks_on_hand: number | null
  weeks_with_inbound: number | null

  planning_lead_time_days: number | null
  replenishment_event_count: number | null
  lead_time_source: string

  quantity_needed_cases: number | null

  active_store_count: number
  units_per_week: number | null
  cases_per_week: number | null

  target_inventory_weeks: number

  skus: SkuRow[]
  stores: StoreRow[]
}


type Tab = "overview" | "inventory" | "stores"


function formatNumber(
  value: number | null | undefined,
  digits = 0
) {
  if (value == null || Number.isNaN(value)) {
    return "—"
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}


function getStatusLabel(status: string) {
  if (status === "critical") {
    return "Critical"
  }

  if (status === "needs_attention") {
    return "Needs attention"
  }

  if (status === "review") {
    return "Review"
  }

  if (status === "healthy") {
    return "Healthy"
  }

  return status
}


function getStatusClasses(status: string) {
  if (status === "critical") {
    return "bg-[#FCE8E1] text-[#B6492D]"
  }

  if (status === "needs_attention") {
    return "bg-[#FBEBD3] text-[#9A641F]"
  }

  if (status === "review") {
    return "bg-[#EEEAF2] text-[#675E7B]"
  }

  return "bg-[#E3EFD9] text-[#3E7A46]"
}


function MetricBlock({
  label,
  value,
  secondary,
  icon,
}: {
  label: string
  value: string
  secondary?: string
  icon: React.ReactNode
}) {
  return (
    <div
      className="rounded-[22px] border px-4 py-4"
      style={{
        background: theme.softSurface,
        borderColor: theme.softLine,
      }}
    >
      <div className="mb-3 flex items-center gap-2">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-xl"
          style={{
            background: "#F3ECE6",
            color: theme.accent,
          }}
        >
          {icon}
        </div>

        <div
          className="text-[11px] font-semibold uppercase tracking-[0.13em]"
          style={{ color: theme.brown }}
        >
          {label}
        </div>
      </div>

      <div
        className="text-[30px] font-semibold tracking-tight"
        style={{ color: theme.charcoal }}
      >
        {value}
      </div>

      {secondary && (
        <div
          className="mt-1 text-sm"
          style={{ color: theme.brown }}
        >
          {secondary}
        </div>
      )}
    </div>
  )
}


export default function DistributionCenterDetailPage() {
  const params = useParams()

  const distributor = String(params.distributor ?? "").toUpperCase()
  const dcCode = String(params.dc ?? "").toUpperCase()

  const [data, setData] = useState<DcDetail | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>("overview")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!distributor || !dcCode) {
      return
    }

    const controller = new AbortController()

    async function loadDc() {
      try {
        setLoading(true)
        setError(null)

        const baseUrl =
          process.env.NEXT_PUBLIC_API_URL ??
          "http://localhost:8000"

        const query = new URLSearchParams({
          org_id: "default_org",
          distributor,
          dc: dcCode,
        })

        const response = await fetch(
          `${baseUrl}/inventory/dc-detail?${query.toString()}`,
          {
            signal: controller.signal,
            cache: "no-store",
          }
        )

        if (!response.ok) {
          const body = await response.json().catch(() => null)

          throw new Error(
            body?.detail ??
              `Failed to load ${distributor} ${dcCode}`
          )
        }

        const payload: DcDetail = await response.json()

        setData(payload)
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return
        }

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load distribution center."
        )
      } finally {
        setLoading(false)
      }
    }

    loadDc()

    return () => {
      controller.abort()
    }
  }, [distributor, dcCode])


  const skuCount = data?.skus.length ?? 0

  const urgentSkuCount = useMemo(() => {
    if (!data) {
      return 0
    }

    return data.skus.filter(
      (sku) =>
        sku.status === "needs_order" ||
        sku.lead_time_risk
    ).length
  }, [data])


  if (loading) {
    return (
      <div
        className="min-h-screen px-6 py-10"
        style={{ background: theme.bg }}
      >
        <div className="mx-auto max-w-[1500px]">
          <Card
            className="rounded-[28px] border shadow-sm"
            style={{
              background: theme.surface,
              borderColor: theme.line,
            }}
          >
            <CardContent className="flex min-h-[360px] items-center justify-center">
              <div
                className="flex items-center gap-3 text-sm font-medium"
                style={{ color: theme.brown }}
              >
                <RefreshCw className="h-4 w-4 animate-spin" />
                Loading distribution center…
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }


  if (error || !data) {
    return (
      <div
        className="min-h-screen px-6 py-10"
        style={{ background: theme.bg }}
      >
        <div className="mx-auto max-w-[1500px]">
          <Card
            className="rounded-[28px] border shadow-sm"
            style={{
              background: theme.surface,
              borderColor: theme.line,
            }}
          >
            <CardContent className="p-8">
              <div className="flex items-center gap-3">
                <AlertTriangle
                  className="h-5 w-5"
                  style={{ color: theme.coral }}
                />

                <div
                  className="font-medium"
                  style={{ color: theme.charcoal }}
                >
                  {error ?? "Distribution center not found."}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }


  const recommendationText =
    data.quantity_needed_cases != null
      ? `${formatNumber(data.quantity_needed_cases)} cases needed`
      : "Recommendation pending"

  return (
    <div
      className="min-h-screen px-5 py-7 md:px-8 md:py-9"
      style={{ background: theme.bg }}
    >
      <div className="mx-auto max-w-[1500px] space-y-5">

        {/* -------------------------------------------------- */}
        {/* HEADER */}
        {/* -------------------------------------------------- */}

        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div
              className="mb-2 text-xs font-semibold uppercase tracking-[0.15em]"
              style={{ color: theme.accent }}
            >
              {data.distributor} · {data.dc}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <h1
                className="text-3xl font-semibold tracking-tight md:text-4xl"
                style={{ color: theme.charcoal }}
              >
                {data.dc_name}
              </h1>

              <span
                className={`rounded-full px-3 py-1.5 text-xs font-semibold ${getStatusClasses(
                  data.status
                )}`}
              >
                {getStatusLabel(data.status)}
              </span>
            </div>

            <div
              className="mt-2 text-sm"
              style={{ color: theme.brown }}
            >
              Distribution center inventory and downstream demand
            </div>
          </div>

          <button
            className="inline-flex items-center justify-center gap-2 rounded-2xl border px-4 py-2.5 text-sm font-medium transition hover:bg-white"
            style={{
              color: theme.brown,
              borderColor: theme.line,
              background: theme.surface,
            }}
          >
            <ArrowDownToLine className="h-4 w-4" />
            Export
          </button>
        </div>


        {/* -------------------------------------------------- */}
        {/* TABS */}
        {/* -------------------------------------------------- */}

        <div className="flex gap-2">
          {[
            ["overview", "Overview"],
            ["inventory", "Inventory Snapshot"],
            ["stores", "Stores"],
          ].map(([value, label]) => {
            const selected = activeTab === value

            return (
              <button
                key={value}
                onClick={() => setActiveTab(value as Tab)}
                className="rounded-full px-4 py-2 text-sm font-medium transition"
                style={{
                  background: selected
                    ? theme.charcoal
                    : "transparent",
                  color: selected
                    ? "#FFFFFF"
                    : theme.brown,
                }}
              >
                {label}
              </button>
            )
          })}
        </div>


        {/* -------------------------------------------------- */}
        {/* OVERVIEW */}
        {/* -------------------------------------------------- */}

        {activeTab === "overview" && (
          <div className="space-y-5">
            <Card
              className="overflow-hidden rounded-[28px] border shadow-sm"
              style={{
                background: theme.surface,
                borderColor: theme.line,
              }}
            >
              <CardContent className="p-0">
                <div className="grid lg:grid-cols-[1.1fr_0.9fr]">

                  {/* LEFT */}
                  <div className="p-6 md:p-7 lg:border-r"
                    style={{ borderColor: theme.line }}
                  >
                    <div className="mb-5">
                      <div
                        className="text-xs font-semibold uppercase tracking-[0.14em]"
                        style={{ color: theme.accent }}
                      >
                        Inventory position
                      </div>

                      <h2
                        className="mt-1 text-xl font-semibold"
                        style={{ color: theme.charcoal }}
                      >
                        Current DC health
                      </h2>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      <MetricBlock
                        label="On hand"
                        value={`${formatNumber(
                          data.quantity_on_hand_cases
                        )} cases`}
                        secondary={`${formatNumber(
                          data.quantity_on_hand_units
                        )} units`}
                        icon={<Box className="h-4 w-4" />}
                      />

                      <MetricBlock
                        label="On PO"
                        value={`${formatNumber(
                          data.quantity_on_po_cases
                        )} cases`}
                        secondary={`${formatNumber(
                          data.quantity_on_po_units
                        )} units`}
                        icon={<PackageCheck className="h-4 w-4" />}
                      />

                      <MetricBlock
                        label="Weeks on hand"
                        value={`${formatNumber(
                          data.weeks_on_hand,
                          1
                        )} wks`}
                        secondary="Current inventory"
                        icon={<Warehouse className="h-4 w-4" />}
                      />

                      <MetricBlock
                        label="With inbound"
                        value={`${formatNumber(
                          data.weeks_with_inbound,
                          1
                        )} wks`}
                        secondary={`${data.target_inventory_weeks}-week target`}
                        icon={<TrendingUp className="h-4 w-4" />}
                      />

                      <MetricBlock
                        label="Est. lead time"
                        value={
                          data.planning_lead_time_days != null
                            ? `${formatNumber(
                                data.planning_lead_time_days
                              )} days`
                            : "—"
                        }
                        secondary={
                          data.lead_time_source === "observed_history"
                            ? `${formatNumber(
                                data.replenishment_event_count
                              )} observed deliveries`
                            : data.lead_time_source === "user_override"
                              ? "User provided"
                              : "Not yet available"
                        }
                        icon={<Clock3 className="h-4 w-4" />}
                      />

                      <MetricBlock
                        label="Quantity needed"
                        value={
                          data.quantity_needed_cases != null
                            ? `${formatNumber(
                                data.quantity_needed_cases
                              )} cases`
                            : "Pending"
                        }
                        secondary={`Target: ${data.target_inventory_weeks} weeks`}
                        icon={<AlertTriangle className="h-4 w-4" />}
                      />
                    </div>


                    <div
                      className="mt-5 rounded-[22px] border px-5 py-4"
                      style={{
                        background: "#FBF2EE",
                        borderColor: "#F0D9D0",
                      }}
                    >
                      <div
                        className="text-[11px] font-semibold uppercase tracking-[0.13em]"
                        style={{ color: theme.coralDark }}
                      >
                        Recommendation
                      </div>

                      <div
                        className="mt-1 text-lg font-semibold"
                        style={{ color: theme.charcoal }}
                      >
                        {recommendationText}
                      </div>

                      <div
                        className="mt-1 max-w-3xl text-sm leading-6"
                        style={{ color: theme.brown }}
                      >
                        Current and inbound inventory provide{" "}
                        {formatNumber(
                          data.weeks_with_inbound,
                          1
                        )}{" "}
                        weeks of coverage versus a{" "}
                        {data.target_inventory_weeks}-week target
                        {data.planning_lead_time_days != null
                          ? `, after accounting for an estimated ${formatNumber(
                              data.planning_lead_time_days
                            )}-day replenishment lead time.`
                          : "."}
                      </div>
                    </div>
                  </div>


                  {/* RIGHT */}
                  <div className="flex flex-col p-6 md:p-7">
                    <div className="mb-4 flex items-start justify-between">
                      <div>
                        <div
                          className="text-xs font-semibold uppercase tracking-[0.14em]"
                          style={{ color: theme.accent }}
                        >
                          Downstream demand
                        </div>

                        <h2
                          className="mt-1 text-xl font-semibold"
                          style={{ color: theme.charcoal }}
                        >
                          Stores served
                        </h2>
                      </div>

                      <MapPin
                        className="h-5 w-5"
                        style={{ color: theme.accent }}
                      />
                    </div>


                    {/* Temporary map mock.
                        Real coordinates slot in here once geocoding finishes. */}
                    <div
                      className="relative min-h-[310px] flex-1 overflow-hidden rounded-[24px] border"
                      style={{
                        background:
                          "radial-gradient(circle at center, #F9F4EA 0%, #F2ECE1 100%)",
                        borderColor: theme.softLine,
                      }}
                    >
                      <div className="absolute inset-0 opacity-50">
                        <div className="absolute left-[15%] top-0 h-full w-px bg-[#DFD6C8]" />
                        <div className="absolute left-[37%] top-0 h-full w-px bg-[#DFD6C8]" />
                        <div className="absolute left-[67%] top-0 h-full w-px bg-[#DFD6C8]" />

                        <div className="absolute left-0 top-[22%] h-px w-full bg-[#DFD6C8]" />
                        <div className="absolute left-0 top-[51%] h-px w-full bg-[#DFD6C8]" />
                        <div className="absolute left-0 top-[76%] h-px w-full bg-[#DFD6C8]" />
                      </div>

                      {[
                        [18, 27],
                        [30, 61],
                        [41, 38],
                        [52, 71],
                        [63, 24],
                        [73, 50],
                        [81, 70],
                        [23, 79],
                        [68, 82],
                        [87, 34],
                      ].map(([left, top], index) => (
                        <div
                          key={index}
                          className="absolute h-2.5 w-2.5 rounded-full border-2 border-white shadow-sm"
                          style={{
                            left: `${left}%`,
                            top: `${top}%`,
                            background: theme.secondary,
                          }}
                        />
                      ))}

                      <div
                        className="absolute left-1/2 top-1/2 flex h-12 w-12 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-2xl border-4 border-white shadow-md"
                        style={{
                          background: theme.coral,
                          color: "#FFFFFF",
                        }}
                      >
                        <Warehouse className="h-5 w-5" />
                      </div>

                      <div
                        className="absolute bottom-4 left-4 rounded-full border bg-white/90 px-3 py-1.5 text-xs font-medium shadow-sm backdrop-blur"
                        style={{
                          borderColor: theme.softLine,
                          color: theme.brown,
                        }}
                      >
                        Map positions loading from store geocoding
                      </div>
                    </div>


                    <div className="mt-4 grid grid-cols-3 gap-3">
                      <div>
                        <div
                          className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                          style={{ color: theme.brown }}
                        >
                          Stores
                        </div>

                        <div
                          className="mt-1 text-2xl font-semibold"
                          style={{ color: theme.charcoal }}
                        >
                          {formatNumber(
                            data.active_store_count
                          )}
                        </div>
                      </div>

                      <div>
                        <div
                          className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                          style={{ color: theme.brown }}
                        >
                          Units / Week
                        </div>

                        <div
                          className="mt-1 text-2xl font-semibold"
                          style={{ color: theme.charcoal }}
                        >
                          {formatNumber(
                            data.units_per_week
                          )}
                        </div>
                      </div>

                      <div>
                        <div
                          className="text-[11px] font-semibold uppercase tracking-[0.12em]"
                          style={{ color: theme.brown }}
                        >
                          Cases / Week
                        </div>

                        <div
                          className="mt-1 text-2xl font-semibold"
                          style={{ color: theme.charcoal }}
                        >
                          {formatNumber(
                            data.cases_per_week,
                            1
                          )}
                        </div>
                      </div>
                    </div>

                    <button
                      className="mt-5 inline-flex w-fit items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold text-white"
                      style={{
                        background: theme.charcoal,
                      }}
                    >
                      <Store className="h-4 w-4" />
                      Add Stores
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}


        {/* -------------------------------------------------- */}
        {/* INVENTORY SNAPSHOT */}
        {/* -------------------------------------------------- */}

        {activeTab === "inventory" && (
          <Card
            className="rounded-[28px] border shadow-sm"
            style={{
              background: theme.surface,
              borderColor: theme.line,
            }}
          >
            <CardContent className="p-6 md:p-7">
              <div className="mb-5 flex items-end justify-between">
                <div>
                  <div
                    className="text-xs font-semibold uppercase tracking-[0.14em]"
                    style={{ color: theme.accent }}
                  >
                    Inventory snapshot
                  </div>

                  <h2
                    className="mt-1 text-xl font-semibold"
                    style={{ color: theme.charcoal }}
                  >
                    {skuCount} SKUs at {data.dc}
                  </h2>
                </div>

                <div
                  className="text-sm"
                  style={{ color: theme.brown }}
                >
                  {urgentSkuCount} need attention
                </div>
              </div>

              <div className="space-y-3">
                {data.skus.map((sku) => (
                  <div
                    key={sku.sku}
                    className="grid items-center gap-4 rounded-[22px] border px-4 py-4 lg:grid-cols-[minmax(220px,1.5fr)_repeat(6,minmax(90px,1fr))]"
                    style={{
                      background: theme.softSurface,
                      borderColor: theme.softLine,
                    }}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div
                        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
                        style={{
                          background: "#F2EDE5",
                          color: theme.accent,
                        }}
                      >
                        <Box className="h-5 w-5" />
                      </div>

                      <div className="min-w-0">
                        <div
                          className="truncate font-semibold"
                          style={{ color: theme.charcoal }}
                        >
                          {sku.product_name}
                        </div>

                        <div
                          className="mt-0.5 text-xs"
                          style={{ color: theme.brown }}
                        >
                          {formatNumber(
                            sku.units_per_case
                          )}{" "}
                          units / case
                        </div>
                      </div>
                    </div>

                    <SnapshotMetric
                      label="On Hand"
                      value={`${formatNumber(
                        sku.quantity_on_hand_cases
                      )} cs`}
                    />

                    <SnapshotMetric
                      label="On PO"
                      value={`${formatNumber(
                        sku.quantity_on_po_cases
                      )} cs`}
                    />

                    <SnapshotMetric
                      label="Units / Wk"
                      value={formatNumber(
                        sku.units_per_week
                      )}
                    />

                    <SnapshotMetric
                      label="WOH"
                      value={formatNumber(
                        sku.weeks_on_hand,
                        1
                      )}
                    />

                    <SnapshotMetric
                      label="WOH + PO"
                      value={formatNumber(
                        sku.weeks_with_inbound,
                        1
                      )}
                    />

                    <div>
                      <div
                        className="text-[10px] font-semibold uppercase tracking-[0.12em]"
                        style={{ color: theme.brown }}
                      >
                        Needed
                      </div>

                      <div
                        className="mt-1 text-lg font-semibold"
                        style={{ color: theme.charcoal }}
                      >
                        {sku.recommended_cases_to_send == null
                          ? "Pending"
                          : `${formatNumber(
                              sku.recommended_cases_to_send
                            )} cs`}
                      </div>

                      <div className="mt-1">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-[10px] font-semibold ${getStatusClasses(
                            sku.status === "needs_order"
                              ? "needs_attention"
                              : sku.status
                          )}`}
                        >
                          {sku.status === "needs_order"
                            ? "Needs order"
                            : getStatusLabel(sku.status)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}


        {/* -------------------------------------------------- */}
        {/* STORES */}
        {/* -------------------------------------------------- */}

        {activeTab === "stores" && (
          <Card
            className="rounded-[28px] border shadow-sm"
            style={{
              background: theme.surface,
              borderColor: theme.line,
            }}
          >
            <CardContent className="p-6 md:p-7">
              <div className="mb-5">
                <div
                  className="text-xs font-semibold uppercase tracking-[0.14em]"
                  style={{ color: theme.accent }}
                >
                  Downstream network
                </div>

                <h2
                  className="mt-1 text-xl font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  {formatNumber(
                    data.active_store_count
                  )} active stores
                </h2>

                <div
                  className="mt-1 text-sm"
                  style={{ color: theme.brown }}
                >
                  Store-level demand metrics can be layered in next.
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {data.stores.map((store, index) => (
                  <div
                    key={`${store.coded_customer}-${index}`}
                    className="rounded-[20px] border px-4 py-4"
                    style={{
                      background: theme.softSurface,
                      borderColor: theme.softLine,
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
                        style={{
                          background: "#F2EDE5",
                          color: theme.accent,
                        }}
                      >
                        <Building2 className="h-4 w-4" />
                      </div>

                      <div className="min-w-0">
                        <div
                          className="truncate text-sm font-semibold"
                          style={{ color: theme.charcoal }}
                        >
                          {store.coded_customer ??
                            "Unnamed store"}
                        </div>

                        <div
                          className="mt-1 text-xs"
                          style={{ color: theme.brown }}
                        >
                          {[
                            store.chain,
                            store.channel,
                            store.state,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}


function SnapshotMetric({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div>
      <div
        className="text-[10px] font-semibold uppercase tracking-[0.12em]"
        style={{ color: theme.brown }}
      >
        {label}
      </div>

      <div
        className="mt-1 text-lg font-semibold"
        style={{ color: theme.charcoal }}
      >
        {value}
      </div>
    </div>
  )
}