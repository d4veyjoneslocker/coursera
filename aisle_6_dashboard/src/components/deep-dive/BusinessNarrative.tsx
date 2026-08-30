"use client"

import { useEffect, useMemo, useState } from "react"
import { ChevronDown } from "lucide-react"

type DriverKey = "new" | "ramping" | "mature"

type NarrativeNode = {
  node_type: string
  driver_type: DriverKey | null
  scope: Record<string, string>
  impact: number | null
  surfaced_by: string
  metrics: Record<string, number | string | null>
  classification: {
    frame?: string | null
    valence?: string | null
    health?: string | null
    emphasis?: string | null
    note?: string | null
  }
  headline: string
  detail: string | null
  children: NarrativeNode[]
}

type NarrativeResponse = {
  current_period: { start: string; end: string }
  prior_period: { start: string; end: string }
  narrative_tree: NarrativeNode[]
}

const theme = {
  surface: "#FFFEFB",
  line: "#DED8CF",
  brown: "#8C6F5A",
  charcoal: "#343332",
  muted: "#9A8A7C",
  blue: "#79A8CF",
  blueDark: "#5E8EAF",
  blueLight: "#ADC9DD",
  red: "#A96552",
  redLight: "#C99B8D",
  track: "#EEEAE3",
}

export default function BusinessNarrativeSummary({ orgId }: { orgId: string }) {
  const [data, setData] = useState<NarrativeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openDriver, setOpenDriver] = useState<DriverKey | null>(null)

  useEffect(() => {
    if (!orgId) return

    let cancelled = false

    async function fetchNarrative() {
      try {
        setLoading(true)
        setError(null)

        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""
        const response = await fetch(
          `${apiBase}/business-analysis/tree?org_id=${encodeURIComponent(orgId)}`
        )

        if (!response.ok) {
          throw new Error(`Business narrative request failed (${response.status})`)
        }

        const json: NarrativeResponse = await response.json()

        if (!cancelled) setData(json)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load business narrative")
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchNarrative()
    return () => {
      cancelled = true
    }
  }, [orgId])

  const drivers = useMemo(() => {
    const map: Partial<Record<DriverKey, NarrativeNode>> = {}
    for (const node of data?.narrative_tree ?? []) {
      if (node.driver_type === "new" || node.driver_type === "ramping" || node.driver_type === "mature") {
        map[node.driver_type] = node
      }
    }
    return map
  }, [data])

  const newNode = drivers.new
  const rampingNode = drivers.ramping
  const matureNode = drivers.mature

  const newImpact = newNode?.impact ?? 0
  const rampingImpact = rampingNode?.impact ?? 0
  const matureImpact = matureNode?.impact ?? 0
  const netChange = newImpact + rampingImpact + matureImpact

  const maxImpact = Math.max(
    Math.abs(newImpact),
    Math.abs(rampingImpact),
    Math.abs(matureImpact),
    1
  )

  const getWidth = (value: number) => (Math.abs(value) / maxImpact) * 47

  function toggle(driver: DriverKey) {
    setOpenDriver((current) => (current === driver ? null : driver))
  }

  if (loading) {
    return (
      <div className="py-8 text-[13px]" style={{ color: theme.muted }}>
        Loading business story…
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-8 text-[13px]" style={{ color: theme.red }}>
        {error}
      </div>
    )
  }

  if (!data) return null

  return (
    <div>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em]"
            style={{ color: theme.brown }}
          >
            Net Unit Change
          </p>

          <div className="mt-3 flex items-end gap-3">
            <p
              className="text-[52px] font-semibold leading-none tracking-[-0.06em]"
              style={{ color: netChange >= 0 ? theme.blue : theme.red }}
            >
              {formatCompact(netChange)}
            </p>
            <p className="pb-1 text-[14px]" style={{ color: theme.brown }}>
              units
            </p>
          </div>

          <p
            className="mt-5 max-w-md text-[16px] leading-7"
            style={{ color: theme.charcoal }}
          >
            <strong>{newNode?.headline}</strong>
          </p>

          {newNode?.detail && (
            <p
              className="mt-3 max-w-md text-[13px] leading-6"
              style={{ color: theme.brown }}
            >
              {newNode.detail}
            </p>
          )}
        </div>

        <div
          className="rounded-[18px] border px-5 py-5"
          style={{ backgroundColor: theme.surface, borderColor: theme.line }}
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p
                className="text-[11px] font-medium uppercase tracking-[0.16em]"
                style={{ color: theme.brown }}
              >
                Change Decomposition
              </p>
              <p className="mt-2 text-[13px]" style={{ color: theme.brown }}>
                What added to — and pulled against — growth
              </p>
            </div>
            <p className="text-[12px] font-medium" style={{ color: theme.charcoal }}>
              Net {formatCompact(netChange)}
            </p>
          </div>

          <div className="mt-7">
            <div className="grid grid-cols-[110px_1fr] gap-3">
              <div />
              <div
                className="grid grid-cols-2 text-[9px] font-medium uppercase tracking-[0.12em]"
                style={{ color: theme.muted }}
              >
                <span className="pr-3 text-right">Drag</span>
                <span className="pl-3">Contribution</span>
              </div>
            </div>

            <div className="mt-2 space-y-5">
              {newNode && (
                <ContributionRow
                  label="New"
                  sublabel="distribution"
                  value={newImpact}
                  width={getWidth(newImpact)}
                  color={newImpact >= 0 ? theme.blue : theme.red}
                />
              )}
              {rampingNode && (
                <ContributionRow
                  label="Ramping"
                  sublabel="recent launches"
                  value={rampingImpact}
                  width={getWidth(rampingImpact)}
                  color={rampingImpact >= 0 ? theme.blueLight : theme.red}
                />
              )}
              {matureNode && (
                <ContributionRow
                  label="Mature"
                  sublabel="established"
                  value={matureImpact}
                  width={getWidth(matureImpact)}
                  color={matureImpact >= 0 ? theme.blueDark : theme.redLight}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 border-t" style={{ borderColor: theme.line }}>
        {newNode && (
          <StoryRow
            headline={newNode.headline}
            detail={newNode.detail}
            impact={newNode.impact}
            isOpen={openDriver === "new"}
            onClick={() => toggle("new")}
          >
            <NodeChildren nodes={newNode.children} driver="new" />
          </StoryRow>
        )}

        {rampingNode && (
          <StoryRow
            headline={rampingNode.headline}
            detail={rampingNode.detail}
            impact={rampingNode.impact}
            isOpen={openDriver === "ramping"}
            onClick={() => toggle("ramping")}
          >
            <div className="grid grid-cols-2 gap-5">
              <BigMetric
                value={formatPercent(rampingNode.metrics.reorder_breadth)}
                label="placements reordered"
              />
              <BigMetric
                value={formatNumber(rampingNode.metrics.avg_reorders, 1)}
                label="avg reorders"
              />
            </div>

            <div className="mt-7">
              <NodeChildren nodes={rampingNode.children} driver="ramping" />
            </div>
          </StoryRow>
        )}

        {matureNode && (
          <StoryRow
            headline={matureNode.headline}
            detail={matureNode.detail}
            impact={matureNode.impact}
            isOpen={openDriver === "mature"}
            onClick={() => toggle("mature")}
          >
            <div className="grid grid-cols-2 gap-5">
              <BigMetric
                value={formatNumber(matureNode.metrics.rate_current, 2)}
                label="current velocity"
              />
              <BigMetric
                value={formatSignedPercent(matureNode.metrics.rate_change)}
                label="velocity change"
              />
            </div>

            <div className="mt-7">
              <NodeChildren nodes={matureNode.children} driver="mature" />
            </div>
          </StoryRow>
        )}
      </div>
    </div>
  )
}

function StoryRow({
  headline,
  detail,
  impact,
  isOpen,
  onClick,
  children,
}: {
  headline: string
  detail: string | null
  impact: number | null
  isOpen: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <div className="border-b last:border-b-0" style={{ borderColor: theme.line }}>
      <button
        type="button"
        onClick={onClick}
        className="flex w-full items-center justify-between gap-6 py-5 text-left"
      >
        <div className="min-w-0">
          <p className="text-[17px] font-medium leading-7" style={{ color: theme.charcoal }}>
            {headline}
          </p>
          {detail && (
            <p className="mt-1 text-[12px] leading-5" style={{ color: theme.muted }}>
              {detail}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-4">
          {impact != null && (
            <p
              className="text-[15px] font-semibold"
              style={{ color: impact >= 0 ? theme.blueDark : theme.red }}
            >
              {formatCompact(impact)}
            </p>
          )}
          <ChevronDown
            size={17}
            strokeWidth={1.8}
            style={{
              color: theme.muted,
              transition: "transform 160ms ease",
              transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
            }}
          />
        </div>
      </button>

      {isOpen && (
        <div className="pb-7">
          <div className="border-t pt-6" style={{ borderColor: theme.line }}>
            {children}
          </div>
        </div>
      )}
    </div>
  )
}

function NodeChildren({
  nodes,
  driver,
  depth = 0,
}: {
  nodes: NarrativeNode[]
  driver: DriverKey
  depth?: number
}) {
  if (!nodes.length) {
    return (
      <p className="text-[12px]" style={{ color: theme.muted }}>
        No additional surfaced drivers.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      {nodes.map((node, index) => (
        <NarrativeEntity
          key={`${driver}-${scopeLabel(node.scope)}-${index}`}
          node={node}
          driver={driver}
          depth={depth}
        />
      ))}
    </div>
  )
}

function NarrativeEntity({
  node,
  driver,
  depth,
}: {
  node: NarrativeNode
  driver: DriverKey
  depth: number
}) {
  const [open, setOpen] = useState(false)
  const hasChildren = node.children.length > 0
  const accent =
    node.surfaced_by === "signal"
      ? theme.red
      : node.impact != null && node.impact < 0
        ? theme.redLight
        : theme.blue

  return (
    <div
      className="border-l-[3px] pl-4"
      style={{
        borderColor: accent,
        marginLeft: depth ? 16 : 0,
      }}
    >
      <button
        type="button"
        disabled={!hasChildren}
        onClick={() => hasChildren && setOpen((value) => !value)}
        className={`w-full text-left ${hasChildren ? "cursor-pointer" : "cursor-default"}`}
      >
        <div className="flex items-start justify-between gap-5">
          <div className="min-w-0">
            {node.surfaced_by === "signal" && (
              <p
                className="mb-1 text-[9px] font-semibold uppercase tracking-[0.13em]"
                style={{ color: theme.red }}
              >
                Watch
              </p>
            )}
            <p className="text-[14px] font-medium leading-6" style={{ color: theme.charcoal }}>
              {node.headline}
            </p>
            {node.detail && (
              <p className="mt-1 max-w-3xl text-[12px] leading-5" style={{ color: theme.muted }}>
                {node.detail}
              </p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-3">
            {node.impact != null && (
              <p className="text-[13px] font-semibold" style={{ color: accent }}>
                {formatCompact(node.impact)}
              </p>
            )}
            {hasChildren && (
              <ChevronDown
                size={15}
                strokeWidth={1.8}
                style={{
                  color: theme.muted,
                  transition: "transform 160ms ease",
                  transform: open ? "rotate(180deg)" : "rotate(0deg)",
                }}
              />
            )}
          </div>
        </div>
      </button>

      <EntityMetricLine node={node} driver={driver} />

      {open && hasChildren && (
        <div className="mt-5 border-t pt-5" style={{ borderColor: theme.line }}>
          <NodeChildren nodes={node.children} driver={driver} depth={depth + 1} />
        </div>
      )}
    </div>
  )
}

function EntityMetricLine({
  node,
  driver,
}: {
  node: NarrativeNode
  driver: DriverKey
}) {
  if (driver === "new") {
    return (
      <p className="mt-2 text-[11px]" style={{ color: theme.brown }}>
        {formatInteger(node.metrics.placements_added)} placements ·{" "}
        {formatInteger(node.metrics.stores_with_new_placements)} stores
      </p>
    )
  }

  if (driver === "ramping") {
    return (
      <p className="mt-2 text-[11px]" style={{ color: theme.brown }}>
        {formatPercent(node.metrics.reorder_breadth)} reordered ·{" "}
        {formatNumber(node.metrics.avg_reorders, 1)} avg reorders
      </p>
    )
  }

  return (
    <p className="mt-2 text-[11px]" style={{ color: theme.brown }}>
      {formatNumber(node.metrics.rate_current, 2)} velocity ·{" "}
      {formatSignedPercent(node.metrics.rate_change)} vs prior period
    </p>
  )
}

function ContributionRow({
  label,
  sublabel,
  value,
  width,
  color,
}: {
  label: string
  sublabel: string
  value: number
  width: number
  color: string
}) {
  const positive = value >= 0

  return (
    <div className="grid grid-cols-[110px_1fr] items-center gap-3">
      <div>
        <p
          className="text-[14px] font-semibold uppercase tracking-[0.07em]"
          style={{ color: theme.brown }}
        >
          {label}
        </p>
        <p className="mt-1 text-[10px]" style={{ color: theme.muted }}>
          {sublabel}
        </p>
      </div>

      <div className="relative h-8">
        <div
          className="absolute left-1/2 top-0 h-full w-px"
          style={{ backgroundColor: "#CEC7BD" }}
        />
        <div
          className={`absolute top-1/2 flex h-5 -translate-y-1/2 items-center ${
            positive
              ? "left-1/2 justify-end rounded-r-[2px] pr-2"
              : "right-1/2 justify-start rounded-l-[2px] pl-2"
          }`}
          style={{
            width: `${Math.max(width, 8)}%`,
            backgroundColor: color,
          }}
        >
          <span className="whitespace-nowrap text-[10px] font-semibold text-white">
            {formatCompact(value)}
          </span>
        </div>
      </div>
    </div>
  )
}

function BigMetric({
  value,
  label,
}: {
  value: string
  label: string
}) {
  return (
    <div className="border-l-[3px] pl-4" style={{ borderColor: "#D5D0C9" }}>
      <p
        className="text-[30px] font-semibold tracking-[-0.04em]"
        style={{ color: theme.charcoal }}
      >
        {value}
      </p>
      <p
        className="mt-1 text-[10px] font-medium uppercase tracking-[0.12em]"
        style={{ color: theme.muted }}
      >
        {label}
      </p>
    </div>
  )
}

function formatCompact(value: number) {
  const sign = value > 0 ? "+" : value < 0 ? "−" : ""
  const abs = Math.abs(value)
  if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(1)}K`
  return `${sign}${abs.toFixed(0)}`
}

function formatPercent(value: unknown) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "—"
}

function formatSignedPercent(value: unknown) {
  if (typeof value !== "number") return "—"
  const sign = value > 0 ? "+" : value < 0 ? "−" : ""
  return `${sign}${Math.abs(value * 100).toFixed(1)}%`
}

function formatNumber(value: unknown, decimals = 1) {
  return typeof value === "number" ? value.toFixed(decimals) : "—"
}

function formatInteger(value: unknown) {
  return typeof value === "number" ? Math.round(value).toLocaleString() : "—"
}

function scopeLabel(scope: Record<string, string>) {
  return Object.values(scope).join(" / ") || "Business"
}
