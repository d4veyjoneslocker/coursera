"use client"

import DashboardHeader from "@/components/ui/DashboardHeader"
import FillRateDeepDive from "@/components/fill-rate/FillRateDeepDive"
import { useOrg } from "@/components/OrgContext"

export default function FillRatePage() {
  const { org } = useOrg()

  return (
    <main className="min-h-screen bg-[#F6F2EA]">
      <DashboardHeader
        activePage="fill-rate"
        dataThrough="September 2026"
        isStale={false}
      />

      <div className="ml-[238px] min-h-screen p-8">
        <div className="mx-auto max-w-7xl space-y-6">
          <div>
            <h1 className="text-[28px] font-semibold tracking-[-0.035em] text-[#343332]">
              Fill Rate
            </h1>

            <p className="mt-1 text-[14px] text-[#8A8179]">
              Understand where retailer demand is being lost to fulfillment
              issues.
            </p>
          </div>

          <FillRateDeepDive orgId={org.id} />
        </div>
      </div>
    </main>
  )
}