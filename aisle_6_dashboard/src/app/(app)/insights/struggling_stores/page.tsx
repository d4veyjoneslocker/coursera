"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import InsightTable from "@/components/InsightsTable"
import { useOrg } from "@/components/OrgContext"

export default function ChainStrugglingStoresPage() {
  const params = useSearchParams()
  const chain = params.get("chain") ?? ""
  const { org } = useOrg()

  const [data, setData] = useState<any>(null)

  useEffect(() => {
    if (!chain || !org?.id) return

    async function load() {
    const url =
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/insights/struggling_stores?org_id=${org.id}&chain=${encodeURIComponent(chain)}`

    console.log("fetching:", url)

    const res = await fetch(url)
    console.log("status:", res.status)

    const json = await res.json()
    console.log("response:", json)

    setData(json)
    }

    load()
  }, [chain, org?.id])

  if (!data) {
    return <div className="p-8">Loading...</div>
  }

  return (
    <div className="min-h-screen bg-[#F6F2EA] p-8">
      <div className="mx-auto max-w-6xl">
        <h1 className="text-2xl font-semibold text-[#343332]">
          {data.title}
        </h1>

        <p className="mt-2 text-sm text-[#705C4F]">
          {data.subtitle}
        </p>

        <InsightTable data={data} />
      </div>
    </div>
  )
}