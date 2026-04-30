"use client"

import { Info } from "lucide-react"
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"

type ChartInfoButtonProps = {
  title?: string
  children?: React.ReactNode
}

export function ChartInfoButton({
  title = "Metric details",
  children,
}: ChartInfoButtonProps) {
  return (
    <HoverCard openDelay={150} closeDelay={100}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          className="
            text-[#A8A29E]
            transition
            hover:text-[#6B6B6B]
          "
        >
          <Info className="h-4 w-4" />
        </button>
      </HoverCardTrigger>

      <HoverCardContent
        align="end"
        sideOffset={8}
        className="
          w-72 rounded-2xl
          border border-[#E5DDD0]
          bg-[#FFFDF9]
          p-4
          shadow-lg
        "
      >
        <div className="space-y-2">
          <div className="text-sm font-semibold text-[#343332]">
            {title}
          </div>

          <div className="text-sm leading-relaxed text-[#705C4F]">
            {children ?? (
              <p>
                Metric definition and calculation details will appear here.
              </p>
            )}
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  )
}