"use client"

import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "next/navigation"
import InsightTable from "@/components/InsightsTable"
import { useOrg } from "@/components/OrgContext"

type InsightTablePageProps = {
  endpoint: string
  requiredParam?: string
  requiredParams?: string[]
  extraParams?: Record<string, string>
}

export default function InsightTablePage({
  endpoint,
  requiredParam = "chain",
  requiredParams,
  extraParams = {},
}: InsightTablePageProps) {
  const params = useSearchParams()
  const { org } = useOrg()

  console.log("URL params:", Object.fromEntries(params.entries()))
  console.log("org:", org)

  const paramKeys = requiredParams ?? [requiredParam]

  const paramValues = useMemo(() => {
    return Object.fromEntries(
      paramKeys.map((key) => [key, params.get(key) ?? ""])
    )
  }, [params, paramKeys.join("|")])

  const [data, setData] = useState<any>(null)

  useEffect(() => {
    const hasAllRequiredParams = paramKeys.every((key) => paramValues[key])

    if (!hasAllRequiredParams || !org?.id) return

    async function load() {
      const search = new URLSearchParams({
        org_id: org.id,
        ...paramValues,
        ...extraParams,
      })

      const url = `${process.env.NEXT_PUBLIC_API_BASE_URL}${endpoint}?${search.toString()}`

      const res = await fetch(url)
      const json = await res.json()

      setData(json)
    }

    load()
  }, [endpoint, org?.id, JSON.stringify(paramValues), JSON.stringify(extraParams)])

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