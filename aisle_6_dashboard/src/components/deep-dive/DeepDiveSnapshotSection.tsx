"use client"

import { useState } from "react"
import DeepDiveSnapshotCard from "./DeepDiveSnapshotCard"

type Theme = {
  surface: string
  line: string
  accent_color: string
  charcoal: string
  primary_color?: string | null
  secondary_color?: string | null
}

type TrendDirection = "up" | "down" | "flat"

export type DeepDiveSnapshotItem = {
  key: string
  label: string
  value: string
  unit?: string
  trendValue?: string
  trendLabel?: string
  trendDirection?: TrendDirection
  interpretation: string
  accentColor?: string | null
  expandedPoints?: string[]
}

type DeepDiveSnapshotSectionProps = {
  cards: DeepDiveSnapshotItem[]
  theme: Theme
  title?: string
  subtitle?: string
}

export default function DeepDiveSnapshotSection({
  cards,
  theme,
}: DeepDiveSnapshotSectionProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)

  if (!cards.length) return null

  return (
    <section className="space-y-4">

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card, index) => {
          const fallbackColors = [
            theme.primary_color,
            theme.secondary_color,
            theme.accent_color,
            theme.charcoal,
          ].filter(Boolean) as string[]

          const accentColor =
            card.accentColor ||
            fallbackColors[index % fallbackColors.length] ||
            theme.accent_color

          const isExpanded = expandedIndex === index

          return (
            <DeepDiveSnapshotCard
              key={card.key}
              label={card.label}
              value={card.value}
              unit={card.unit}
              trendValue={card.trendValue}
              trendLabel={card.trendLabel}
              trendDirection={card.trendDirection}
              interpretation={card.interpretation}
              accentColor={accentColor}
              theme={theme}
              isExpanded={isExpanded}
              expandedPoints={card.expandedPoints}
              onToggle={() =>
                setExpandedIndex(isExpanded ? null : index)
              }
            />
          )
        })}
      </div>
    </section>
  )
}