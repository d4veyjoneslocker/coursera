"use client"

import { createContext, useContext, useEffect, useState } from "react"
import { supabase } from "@/lib/supabase"

export type Org = {
  id: string
  name: string
  primary_color: string | null
  secondary_color: string | null
  accent_color: string | null
  background_color: string | null
  logo_url: string | null
  last_refreshed_at: string | null
  refresh_cadence: string | null
}

type OrgContextValue = {
  org: Org
  skuColors: Record<string, string>
}

const OrgContext = createContext<OrgContextValue | null>(null)

export function OrgProvider({
  org,
  children,
}: {
  org: Org
  children: React.ReactNode
}) {
  const [skuColors, setSkuColors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!org?.id) return

    async function loadSkuColors() {
      const { data, error } = await supabase
        .from("sku_display_colors")
        .select("sku_name,color")
        .eq("org_id", org.id)

      if (error) {
        console.error("Failed to load SKU colors:", error)
        return
      }

      setSkuColors(
        Object.fromEntries(
          (data ?? []).map((row) => [row.sku_name, row.color])
        )
      )
    }

    loadSkuColors()
  }, [org?.id])

  return (
    <OrgContext.Provider value={{ org, skuColors }}>
      {children}
    </OrgContext.Provider>
  )
}

export function useOrg() {
  const context = useContext(OrgContext)

  if (!context) {
    throw new Error("useOrg must be used inside OrgProvider")
  }

  return context
}