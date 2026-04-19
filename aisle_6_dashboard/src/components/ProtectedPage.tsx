"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { OrgProvider, type Org } from "@/components/OrgContext"

export default function ProtectedPage({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [org, setOrg] = useState<Org | null>(null)

  useEffect(() => {
    const loadAppContext = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session?.user) {
        router.push("/login")
        return
      }

      const { data: profile, error: profileError } = await supabase
        .from("profiles")
        .select("org_id")
        .eq("user_id", session.user.id)
        .single()

      if (profileError || !profile) {
        console.error("PROFILE ERROR:", profileError)
        router.push("/login")
        return
      }

      const { data: orgData, error: orgError } = await supabase
        .from("organizations")
        .select("*")
        .eq("id", profile.org_id)
        .single()

      if (orgError || !orgData) {
        console.error("ORG ERROR:", orgError)
        router.push("/login")
        return
      }

      setOrg(orgData)
      setLoading(false)
    }

    loadAppContext()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session?.user) {
        router.push("/login")
      }
    })

    return () => subscription.unsubscribe()
  }, [router])

  if (loading || !org) {
    return <div className="p-6">Loading...</div>
  }

  return <OrgProvider org={org}>{children}</OrgProvider>
}