"use client"

import { createContext, useContext } from "react"

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

const OrgContext = createContext<Org | null>(null)

export function OrgProvider({
  org,
  children,
}: {
  org: Org
  children: React.ReactNode
}) {
  return <OrgContext.Provider value={org}>{children}</OrgContext.Provider>
}

export function useOrg() {
  const org = useContext(OrgContext)

  if (!org) {
    throw new Error("useOrg must be used inside OrgProvider")
  }

  return org
}