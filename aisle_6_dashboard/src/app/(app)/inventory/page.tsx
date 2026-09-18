"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  CircleAlert,
  Clock3,
  PackageCheck,
  RefreshCw,
  ShieldAlert,
  Truck,
} from "lucide-react"
import LoadingScreen from "@/components/LoadingScreen"

type InventorySummary = {
  dc_count: number
  dcs_needing_action: number
  dcs_monitoring: number
  dcs_needing_review: number
  dcs_with_projection_unavailable: number
  known_recommended_cases: number
}

type Intervention = {
  reaches_oos: boolean | null
  first_oos_date: string | null
  lowest_woh: number | null
  lowest_woh_date: string | null
  first_tolerance_breach_date: string | null
  intervention_required: boolean | null
  intervention_type: string | null
  recommended_cases: number | null
  order_by_date: string | null
  needed_by_date: string | null
  expected_delivery_date: string | null
  po_cases: number | null
  current_po_receipt_date: string | null
}

type OverviewSku = {
  sku: string
  product_name: string
  inventory_status: "healthy" | "monitor" | "action" | null
  inventory_urgency: "normal" | "high" | "critical" | null
  po_status: string | null
  has_active_po: boolean | null
  has_overdue_po: boolean | null
  has_stale_po: boolean | null
  has_projected_order: boolean | null
  has_resolving_projected_order: boolean | null
  days_until_oos: number | null
  days_of_cushion: number | null
  planning_lead_time_days: number | null;
  interventions: Intervention[]
}

type DistributionCenter = {
  distributor: string
  dc: string
  sku_count: number
  skus_needing_action: number
  skus_monitoring: number
  skus_healthy: number
  skus_needing_review: number
  skus_projection_unavailable: number
  skus_to_expedite: number
  skus_needing_new_order: number
  skus_monitoring_projected_order: number
  quantity_needed_cases: number
  recommendation_complete: boolean
  skus: OverviewSku[]
}

type InventoryOverviewResponse = {
  as_of_date?: string
  summary: InventorySummary
  distribution_centers: DistributionCenter[]
}

type SkuWithDc = OverviewSku & {
  distributor: string
  dc: string
  recommendation_complete: boolean
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000"

function formatNumber(value: number | null | undefined, digits = 0) {
  if (value == null || Number.isNaN(value)) return "—"

  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function formatDate(value: string | null | undefined) {
  if (!value) return null

  const date = new Date(`${value.slice(0, 10)}T12:00:00`)
  if (Number.isNaN(date.getTime())) return value

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  })
}

function pluralize(count: number, singular: string, plural = `${singular}s`) {
  return count === 1 ? singular : plural
}

function getNewOrder(sku: SkuWithDc) {
  return sku.interventions.find(
    (item) =>
      item.intervention_required === true &&
      item.intervention_type === "new_order" &&
      (item.recommended_cases ?? 0) > 0
  )
}

function getExpedite(sku: SkuWithDc) {
  return sku.interventions.find(
    (item) =>
      item.intervention_required === true &&
      item.intervention_type === "expedite_po"
  )
}

function getPrimaryIntervention(sku: SkuWithDc) {
  return getNewOrder(sku) ?? getExpedite(sku) ?? sku.interventions[0] ?? null
}

function getProjectedOosDate(sku: SkuWithDc) {
  const oos = sku.interventions.find(
    (item) => item.reaches_oos && item.first_oos_date
  )
  return oos?.first_oos_date ?? null
}

function hasUsableCoverage(sku: SkuWithDc) {
  return sku.has_active_po === true
}

function SummaryCard({
  icon,
  value,
  label,
  detail,
}: {
  icon: React.ReactNode
  value: string
  label: string
  detail: string
}) {
  return (
    <div className="rounded-[24px] border border-[#E5DDD0] bg-[#FFFDF9] p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[28px] font-semibold tracking-[-0.03em] text-[#343332]">
            {value}
          </div>
          <div className="mt-1 text-sm font-medium text-[#343332]">{label}</div>
          <div className="mt-1 text-xs leading-5 text-[#8A8179]">{detail}</div>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#F6F2EA] text-[#705C4F]">
          {icon}
        </div>
      </div>
    </div>
  )
}

function StatusPill({ children, tone }: { children: React.ReactNode; tone: "critical" | "high" | "normal" | "monitor" | "healthy" | "neutral" }) {
  const classes = {
    critical: "border-[#F0C8BE] bg-[#FFF2EE] text-[#B84D34]",
    high: "border-[#E8D5B5] bg-[#FFF8E8] text-[#8A651F]",
    normal: "border-[#DED8E8] bg-[#F6F3FA] text-[#6E6683]",
    monitor: "border-[#D8D2E5] bg-[#F6F3FA] text-[#6E6683]",
    healthy: "border-[#CFE2D6] bg-[#F1F8F3] text-[#55735E]",
    neutral: "border-[#E5DDD0] bg-[#FCFAF6] text-[#705C4F]",
  }

  return (
    <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${classes[tone]}`}>
      {children}
    </span>
  )
}

type DcActionGroup = {
  distributor: string
  dc: string
  items: SkuWithDc[]
  totalRecommendedCases: number
  leadTimeDays: number | null
}

const SKU_IMAGES: Record<
  string,
  { src: string; scale: number; x?: number }
> = {
  "VANILLA BEAN": {
    src: "/skus/smearcase-vanilla-bean.png",
    scale: 1.18,
  },
  "MOCHA JOE": {
    src: "/skus/smearcase-mocha-joe.png",
    scale: 1.14,
    x: -5,
  },
  "STRAWBERRY": {
    src: "/skus/smearcase-strawberry.png",
    scale: 1.0,
  },
  "PEANUT BUTTER": {
    src: "/skus/smearcase-peanut-butter.png",
    scale: 0.92,
  },
}

function getSkuImage(sku: OverviewSku) {
  return SKU_IMAGES[sku.product_name.toUpperCase()] ?? null
}

function groupActionsByDc(items: SkuWithDc[]) {
  const grouped = new Map<string, SkuWithDc[]>()

  for (const sku of items) {
    const key = `${sku.distributor}::${sku.dc}`
    const existing = grouped.get(key) ?? []
    existing.push(sku)
    grouped.set(key, existing)
  }

  return Array.from(grouped.values()).map((dcItems): DcActionGroup => {
    const first = dcItems[0]
    const leadTimes = dcItems
      .map((sku) => sku.planning_lead_time_days)
      .filter((value): value is number => value != null)

    return {
      distributor: first.distributor,
      dc: first.dc,
      items: dcItems,
      totalRecommendedCases: dcItems.reduce(
        (sum, sku) => sum + (getNewOrder(sku)?.recommended_cases ?? 0),
        0
      ),
      leadTimeDays: leadTimes.length > 0 ? leadTimes[0] : null,
    }
  })
}

function ActionSkuRow({
  sku,
  onClick,
  compact = false,
}: {
  sku: SkuWithDc
  onClick: () => void
  compact?: boolean
}) {
  const newOrder = getNewOrder(sku)
  const expedite = getExpedite(sku)
  const primary = getPrimaryIntervention(sku)
  const oosDate = getProjectedOosDate(sku)
  const coverage = hasUsableCoverage(sku)
  const image = getSkuImage(sku)

  const isOutOfStock =
    oosDate != null &&
    new Date(`${oosDate.slice(0, 10)}T00:00:00`).getTime() <=
      new Date().setHours(0, 0, 0, 0)

  const orderByIsPast =
    newOrder?.order_by_date != null &&
    new Date(`${newOrder.order_by_date.slice(0, 10)}T00:00:00`).getTime() <
      new Date().setHours(0, 0, 0, 0)

  const actionTitle = newOrder
    ? `${formatNumber(newOrder.recommended_cases)} cases`
    : expedite
      ? "Follow up on PO"
      : "Review"

  const actionDetail = newOrder
    ? orderByIsPast
      ? "Order ASAP"
      : newOrder.order_by_date
        ? `Order by ${formatDate(newOrder.order_by_date)}`
        : "New order recommended"
    : expedite?.needed_by_date
      ? `Needed by ${formatDate(expedite.needed_by_date)}`
      : "Inventory intervention"

  return (
    <button
      type="button"
      onClick={onClick}
      className={`group grid w-full cursor-pointer gap-4 border-t border-[#EEE5D8] text-left transition hover:bg-[#FCFAF6] ${
        compact
          ? "px-5 py-4 md:grid-cols-[54px_minmax(0,1.3fr)_minmax(150px,0.75fr)_minmax(170px,0.8fr)_36px]"
          : "px-5 py-5 md:grid-cols-[64px_minmax(0,1.3fr)_minmax(150px,0.75fr)_minmax(170px,0.8fr)_36px]"
      } md:items-center`}
    >
      <div
        className={`relative hidden shrink-0 overflow-hidden rounded-2xl border border-[#EEE5D8] bg-[#F6F2EA] md:block ${
          compact ? "h-14 w-12" : "h-16 w-14"
        }`}
      >
        {image ? (
          <Image
            src={image.src}
            alt={sku.product_name}
            fill
            sizes="64px"
            className="object-contain"
            style={{
              transform: `translateX(${image.x ?? 0}px) scale(${image.scale})`,
            }}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-[10px] font-semibold text-[#9A93B0]">
            {sku.sku.slice(0, 2)}
          </div>
        )}
      </div>

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <div className="truncate font-semibold text-[#343332]">{sku.product_name}</div>
          {sku.inventory_urgency && (
            <StatusPill tone={sku.inventory_urgency}>{sku.inventory_urgency}</StatusPill>
          )}
        </div>
        <div className="mt-1 text-xs text-[#8A8179]">{sku.sku}</div>
        <div className="mt-2 flex flex-wrap gap-2">
          <StatusPill tone={coverage ? "neutral" : "critical"}>
            {coverage ? "Confirmed PO" : "No confirmed coverage"}
          </StatusPill>
          {sku.has_overdue_po && <StatusPill tone="high">PO overdue</StatusPill>}
          {sku.has_stale_po && <StatusPill tone="high">Stale PO</StatusPill>}
        </div>
      </div>

      <div>
        <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A09890]">
          Inventory risk
        </div>
        <div className="mt-1 text-sm font-semibold text-[#343332]">
          {isOutOfStock
            ? "Already out of stock"
            : oosDate
              ? `OOS ${formatDate(oosDate)}`
              : primary?.lowest_woh != null
                ? `${formatNumber(primary.lowest_woh, 1)} WOH low`
                : "Below threshold"}
        </div>
        <div className="mt-1 text-xs text-[#8A8179]">
          {sku.planning_lead_time_days != null
            ? `${formatNumber(sku.planning_lead_time_days)}-day lead time`
            : "Lead time unavailable"}
        </div>
      </div>

      <div>
        <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#A09890]">
          SKUba recommendation
        </div>
        <div className="mt-1 text-base font-semibold text-[#343332]">{actionTitle}</div>
        <div className={`mt-1 text-xs ${orderByIsPast ? "font-semibold text-[#C85F43]" : "text-[#8A8179]"}`}>
          {actionDetail}
        </div>
      </div>

      <div className="hidden h-9 w-9 items-center justify-center rounded-full border border-[#E5DDD0] bg-[#FFFDF9] text-[#705C4F] transition group-hover:border-[#C8795A] group-hover:text-[#C8795A] md:flex">
        <ArrowRight className="h-4 w-4" />
      </div>
    </button>
  )
}

function DcActionCard({
  group,
  tone,
  onOpen,
  compact = false,
}: {
  group: DcActionGroup
  tone: "critical" | "high" | "normal"
  onOpen: (sku: SkuWithDc) => void
  compact?: boolean
}) {
  const toneStyles = {
    critical: {
      border: "border-[#EEC4B9]",
      header: "bg-[#FFF7F3]",
      badge: "border-[#E9C8BD] text-[#C85F43]",
    },
    high: {
      border: "border-[#E8D5B5]",
      header: "bg-[#FFFAF0]",
      badge: "border-[#E8D5B5] text-[#8A651F]",
    },
    normal: {
      border: "border-[#DDD7E7]",
      header: "bg-[#F8F5FA]",
      badge: "border-[#DDD7E7] text-[#6E6683]",
    },
  }[tone]

  return (
    <div className={`overflow-hidden rounded-[26px] border bg-[#FFFDF9] shadow-sm ${toneStyles.border}`}>
      <div className={`flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between ${toneStyles.header}`}>
        <div>
          <div className="flex items-center gap-2">
            <span className={`rounded-full border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${toneStyles.badge}`}>
              {group.distributor}
            </span>
            <span className="text-lg font-semibold tracking-[-0.02em] text-[#343332]">{group.dc}</span>
          </div>
          <div className="mt-1.5 text-xs text-[#8A8179]">
            {group.items.length} {pluralize(group.items.length, "SKU")} need attention
            {group.leadTimeDays != null
              ? ` · ${formatNumber(group.leadTimeDays)}-day lead time`
              : ""}
          </div>
        </div>

        {group.totalRecommendedCases > 0 && (
          <div className="sm:text-right">
            <div className="text-lg font-semibold tracking-[-0.02em] text-[#343332]">
              {formatNumber(group.totalRecommendedCases)} cases
            </div>
            <div className="text-[11px] text-[#8A8179]">total recommended</div>
          </div>
        )}
      </div>

      {group.items.map((sku) => (
        <ActionSkuRow
          key={`${sku.distributor}-${sku.dc}-${sku.sku}`}
          sku={sku}
          compact={compact}
          onClick={() => onOpen(sku)}
        />
      ))}
    </div>
  )
}

function WorkflowSection({
  eyebrow,
  title,
  description,
  items,
  tone,
  onOpen,
  compact = false,
}: {
  eyebrow: string
  title: string
  description: string
  items: SkuWithDc[]
  tone: "critical" | "high" | "normal"
  onOpen: (sku: SkuWithDc) => void
  compact?: boolean
}) {
  if (items.length === 0) return null

  const groups = groupActionsByDc(items)

  const eyebrowColor = {
    critical: "text-[#C85F43]",
    high: "text-[#8A651F]",
    normal: "text-[#6E6683]",
  }[tone]

  return (
    <section>
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <div className={`text-[11px] font-semibold uppercase tracking-[0.14em] ${eyebrowColor}`}>
            {eyebrow}
          </div>
          <h2 className="mt-1 text-2xl font-semibold tracking-[-0.03em] text-[#343332]">{title}</h2>
          <p className="mt-1 text-sm text-[#8A8179]">{description}</p>
        </div>
        <div className="hidden rounded-full border border-[#E5DDD0] bg-[#FFFDF9] px-3 py-1.5 text-xs font-medium text-[#8A8179] sm:block">
          {groups.length} {pluralize(groups.length, "DC")} · {items.length} {pluralize(items.length, "SKU")}
        </div>
      </div>

      <div className="space-y-4">
        {groups.map((group) => (
          <DcActionCard
            key={`${group.distributor}-${group.dc}`}
            group={group}
            tone={tone}
            compact={compact}
            onOpen={onOpen}
          />
        ))}
      </div>
    </section>
  )
}

function MonitorRow({ sku, onClick }: { sku: SkuWithDc; onClick: () => void }) {
  const primary = getPrimaryIntervention(sku)
  const projected = sku.has_resolving_projected_order === true

  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full cursor-pointer items-center justify-between gap-4 border-b border-[#EEE5D8] px-5 py-4 text-left last:border-b-0 hover:bg-[#FCFAF6]"
    >
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#F6F3FA] text-[#6E6683]">
          <Truck className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="truncate font-medium text-[#343332]">{sku.product_name}</div>
          <div className="mt-0.5 text-xs text-[#8A8179]">
            {sku.distributor} · {sku.dc}
          </div>
        </div>
      </div>

      <div className="ml-auto hidden text-right sm:block">
        <div className="text-sm font-semibold text-[#343332]">
          {sku.has_overdue_po
            ? "Follow up on overdue PO"
            : projected
              ? "Projected order monitored"
              : sku.has_active_po
                ? "Follow up on PO"
                : "Monitoring"}
        </div>
        <div className="mt-0.5 text-xs text-[#8A8179]">
          {primary?.current_po_receipt_date
            ? `Receipt ${formatDate(primary.current_po_receipt_date)}`
            : primary?.needed_by_date
              ? `Needed ${formatDate(primary.needed_by_date)}`
              : "No new order required now"}
        </div>
      </div>

      <ArrowRight className="h-4 w-4 shrink-0 text-[#A59C93] transition group-hover:text-[#C8795A]" />
    </button>
  )
}

function HealthyRow({ sku, onClick }: { sku: SkuWithDc; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full cursor-pointer items-center justify-between gap-4 border-b border-[#EEE5D8] px-5 py-4 text-left last:border-b-0 hover:bg-[#FCFAF6]"
    >
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#F1F6F2] text-[#55735E]">
          <PackageCheck className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="truncate font-medium text-[#343332]">{sku.product_name}</div>
          <div className="mt-0.5 text-xs text-[#8A8179]">
            {sku.distributor} · {sku.dc}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <StatusPill tone="healthy">Healthy</StatusPill>
        <ArrowRight className="h-4 w-4 text-[#A59C93] transition group-hover:text-[#C8795A]" />
      </div>
    </button>
  )
}

function getImpendingOosDate(sku: SkuWithDc) {
  const oosDate = getProjectedOosDate(sku)

  if (!oosDate) return Number.POSITIVE_INFINITY

  return new Date(`${oosDate.slice(0, 10)}T00:00:00`).getTime()
}

function sortByPriority(items: SkuWithDc[]) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const todayTime = today.getTime()

  return [...items].sort((a, b) => {
    const aOos = getImpendingOosDate(a)
    const bOos = getImpendingOosDate(b)
    const aIsOos = aOos <= todayTime
    const bIsOos = bOos <= todayTime

    if (aIsOos !== bIsOos) return aIsOos ? -1 : 1
    if (aIsOos && bIsOos) return aOos - bOos

    const aCushion = a.days_of_cushion ?? Number.POSITIVE_INFINITY
    const bCushion = b.days_of_cushion ?? Number.POSITIVE_INFINITY

    if (aCushion !== bCushion) return aCushion - bCushion

    return aOos - bOos
  })
}

export default function InventoryPage() {
  const router = useRouter()
  const [data, setData] = useState<InventoryOverviewResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadInventory = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      params.set("org_id", "default_org")

      const response = await fetch(
        `${API_BASE_URL}/inventory/overview?${params.toString()}`,
        { cache: "no-store" }
      )

      if (!response.ok) {
        throw new Error(`Inventory overview failed: ${response.status}`)
      }

      const json: InventoryOverviewResponse = await response.json()
      setData(json)
    } catch (err) {
      console.error("Failed to load inventory overview:", err)
      setError("Unable to load inventory planning.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInventory()
  }, [])

  const groups = useMemo(() => {
    const allSkus: SkuWithDc[] = []
    const reviewDcs: DistributionCenter[] = []

    for (const dc of data?.distribution_centers ?? []) {
      if (
        !dc.recommendation_complete ||
        dc.skus_needing_review > 0 ||
        dc.skus_projection_unavailable > 0
      ) {
        reviewDcs.push(dc)
      }

      for (const sku of dc.skus ?? []) {
        allSkus.push({
          ...sku,
          distributor: dc.distributor,
          dc: dc.dc,
          recommendation_complete: dc.recommendation_complete,
        })
      }
    }

    const action = allSkus.filter((sku) => sku.inventory_status === "action")
    const monitor = allSkus.filter((sku) => sku.inventory_status === "monitor")
    const healthy = allSkus.filter((sku) => sku.inventory_status === "healthy")

    const handleToday = action.filter((sku) => sku.inventory_urgency === "critical")
    const handleThisWeek = action.filter((sku) => sku.inventory_urgency === "high")
    const upcoming = action.filter((sku) => sku.inventory_urgency === "normal")

    const monitorFollowUp = monitor.filter(
      (sku) =>
        sku.has_active_po === true ||
        sku.has_overdue_po === true ||
        sku.has_stale_po === true
    )

    const otherMonitoring = monitor.filter((sku) => !monitorFollowUp.includes(sku))

    return {
      allSkus,
      action,
      handleToday: sortByPriority(handleToday),
      handleThisWeek: sortByPriority(handleThisWeek),
      upcoming: sortByPriority(upcoming),
      monitorFollowUp: sortByPriority(monitorFollowUp),
      otherMonitoring: sortByPriority(otherMonitoring),
      healthy: sortByPriority(healthy),
      reviewDcs,
    }
  }, [data])

  const openSku = (sku: SkuWithDc) => {
    router.push(
      `/inventory/${encodeURIComponent(sku.distributor)}/${encodeURIComponent(sku.dc)}`
    )
  }

  const openDc = (dc: DistributionCenter) => {
    router.push(
      `/inventory/${encodeURIComponent(dc.distributor)}/${encodeURIComponent(dc.dc)}`
    )
  }

  if (loading) {
    return <LoadingScreen mode="inventory-overview" />
  }

    if (error || !data) {
      return (
        <div className="min-h-screen bg-[#F6F2EA] px-6 py-10">
          <div className="mx-auto max-w-7xl">
            <div className="rounded-[26px] border border-[#F0C8BE] bg-[#FFF7F4] p-6">
              <div className="flex items-start gap-3">
                <CircleAlert className="mt-0.5 h-5 w-5 text-[#C8795A]" />
                <div>
                  <div className="font-semibold text-[#343332]">Inventory planning could not load</div>
                  <div className="mt-1 text-sm text-[#8A8179]">{error ?? "No inventory data was returned."}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    }

  return (
    <main className="min-h-screen bg-[#F6F2EA] p-6 md:p-8">
      <div className="mx-auto max-w-7xl space-y-8">
        <header className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9A93B0]">Inventory</div>
            <h1 className="mt-2 text-[34px] font-semibold tracking-[-0.04em] text-[#343332]">Inventory Planning</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#7C746D]">
              Start with what needs attention now, then work down through this week&apos;s actions and monitored supply.
            </p>
          </div>

          <button
            type="button"
            onClick={loadInventory}
            className="inline-flex w-fit items-center gap-2 rounded-full border border-[#E5DDD0] bg-[#FFFDF9] px-4 py-2.5 text-sm font-medium text-[#705C4F] shadow-sm transition hover:border-[#D8CCBC]"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </header>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            icon={<ShieldAlert className="h-5 w-5" />}
            value={formatNumber(groups.handleToday.length)}
            label="Critical SKUs"
            detail="Inventory requiring the fastest attention"
          />
          <SummaryCard
            icon={<AlertTriangle className="h-5 w-5" />}
            value={formatNumber(groups.action.length)}
            label="SKUs need action"
            detail={`Across ${data.summary.dcs_needing_action} ${pluralize(data.summary.dcs_needing_action, "DC")}`}
          />
          <SummaryCard
            icon={<Boxes className="h-5 w-5" />}
            value={formatNumber(data.summary.known_recommended_cases)}
            label="Cases recommended"
            detail="Active new-order recommendations"
          />
          <SummaryCard
            icon={<Truck className="h-5 w-5" />}
            value={formatNumber(groups.monitorFollowUp.length + groups.otherMonitoring.length)}
            label="SKUs monitoring"
            detail="Supply being watched without a new order now"
          />
        </div>

        <WorkflowSection
          eyebrow="Handle today"
          title="Do these before you finish today"
          description="Critical inventory work, grouped by DC so each card maps to an ordering workflow."
          items={groups.handleToday}
          tone="critical"
          onOpen={openSku}
        />

        <WorkflowSection
          eyebrow="Handle this week"
          title="Next in the queue"
          description="High-urgency inventory work that should be handled after today's critical queue."
          items={groups.handleThisWeek}
          tone="high"
          onOpen={openSku}
        />

        <WorkflowSection
          eyebrow="Upcoming"
          title="Planned inventory actions"
          description="These interventions have more cushion and can wait until the higher-priority work is complete."
          items={groups.upcoming}
          tone="normal"
          compact
          onOpen={openSku}
        />

        {(groups.monitorFollowUp.length > 0 || groups.otherMonitoring.length > 0) && (
          <section>
            <div className="mb-4 flex items-end justify-between gap-4">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9A93B0]">Monitor</div>
                <h2 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-[#343332]">Supply to keep an eye on</h2>
                <p className="mt-1 text-sm text-[#8A8179]">No new order is required now, but these SKUs still deserve visibility.</p>
              </div>
              <div className="text-xs font-medium text-[#A09890]">
                {groups.monitorFollowUp.length + groups.otherMonitoring.length} {pluralize(groups.monitorFollowUp.length + groups.otherMonitoring.length, "SKU")}
              </div>
            </div>

            <div className="overflow-hidden rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] shadow-sm">
              {[...groups.monitorFollowUp, ...groups.otherMonitoring].map((sku) => (
                <MonitorRow
                  key={`${sku.distributor}-${sku.dc}-${sku.sku}`}
                  sku={sku}
                  onClick={() => openSku(sku)}
                />
              ))}
            </div>
          </section>
        )}

        {groups.reviewDcs.length > 0 && (
          <section>
            <div className="mb-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9A93B0]">Review</div>
              <h2 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-[#343332]">Projection unavailable</h2>
              <p className="mt-1 text-sm text-[#8A8179]">Relevant inventory exists here, but SKUba cannot complete every projection.</p>
            </div>

            <div className="overflow-hidden rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] shadow-sm">
              {groups.reviewDcs.map((dc) => (
                <button
                  type="button"
                  key={`${dc.distributor}-${dc.dc}`}
                  onClick={() => openDc(dc)}
                  className="group flex w-full items-center justify-between gap-4 border-b border-[#EEE5D8] px-5 py-4 text-left last:border-b-0 hover:bg-[#FCFAF6]"
                >
                  <div>
                    <div className="font-medium text-[#343332]">{dc.distributor} · {dc.dc}</div>
                    <div className="mt-1 text-xs text-[#8A8179]">
                      {dc.skus_projection_unavailable} projection unavailable · {dc.skus_needing_review} need review
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-[#A59C93] transition group-hover:text-[#C8795A]" />
                </button>
              ))}
            </div>
          </section>
        )}

        <section>
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#55735E]">Healthy</div>
              <h2 className="mt-1 text-xl font-semibold tracking-[-0.02em] text-[#343332]">No intervention needed</h2>
            </div>
            <div className="text-xs font-medium text-[#A09890]">
              {groups.healthy.length} {pluralize(groups.healthy.length, "SKU")}
            </div>
          </div>

          <div className="overflow-hidden rounded-[26px] border border-[#E5DDD0] bg-[#FFFDF9] shadow-sm">
            {groups.healthy.length > 0 ? (
              groups.healthy.map((sku) => (
                <HealthyRow
                  key={`${sku.distributor}-${sku.dc}-${sku.sku}`}
                  sku={sku}
                  onClick={() => openSku(sku)}
                />
              ))
            ) : (
              <div className="px-5 py-5 text-sm text-[#8A8179]">No healthy SKUs to show.</div>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}
