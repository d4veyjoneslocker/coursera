"use client"

import { useState } from "react"

type InsightDefinition = {
  whatItIs: string
  howItsCalculated: string
  whyItMatters: string
}

type InsightDescriptionProps = {
  definition: InsightDefinition
}

export default function InsightDescription({
  definition,
}: InsightDescriptionProps) {
  const [isOpen, setIsOpen] = useState(false)

  const {
    whatItIs,
    howItsCalculated,
    whyItMatters,
  } = definition

  return (
    <div className="relative shrink-0">
      {/* Info button */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex h-7 w-7 items-center justify-center rounded-full border border-[#DDD5CA] text-[12px] font-semibold text-[#9A8A7C] transition hover:bg-[#F4F1EC] hover:text-[#705C4F]"
        aria-label="About this insight"
        aria-expanded={isOpen}
      >
        i
      </button>

      {/* Description popover */}
      {isOpen && (
        <div className="absolute right-0 top-9 z-50 w-[340px] rounded-2xl border border-[#E8E0D5] bg-[#FFFEFB] p-5 shadow-lg">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9A8A7C]">
              What it is
            </p>

            <p className="mt-1.5 text-[13px] leading-5 text-[#705C4F]">
              {whatItIs}
            </p>
          </div>

          <div className="mt-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9A8A7C]">
              How it&apos;s calculated
            </p>

            <p className="mt-1.5 text-[13px] leading-5 text-[#705C4F]">
              {howItsCalculated}
            </p>
          </div>

          <div className="mt-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#9A8A7C]">
              Why it matters
            </p>

            <p className="mt-1.5 text-[13px] leading-5 text-[#705C4F]">
              {whyItMatters}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}