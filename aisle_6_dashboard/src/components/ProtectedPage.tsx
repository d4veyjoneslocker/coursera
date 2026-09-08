"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

import { supabase } from "@/lib/supabase"
import { OrgProvider, type Org } from "@/components/OrgContext"
import LoadingScreen from "@/components/LoadingScreen"

export default function ProtectedPage({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [org, setOrg] = useState<Org | null>(null)

  useEffect(() => {
    const loadAppContext = async () => {
      setLoading(true)
      setError("")

      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session?.user) {
        router.replace("/login")
        return
      }

      const { data: profile, error: profileError } = await supabase
        .from("profiles")
        .select("org_id")
        .eq("user_id", session.user.id)
        .single()

      if (profileError || !profile) {
        setError(
          "Your account exists, but it is not linked to an organization yet."
        )
        setLoading(false)
        return
      }

      const { data: orgData, error: orgError } = await supabase
        .from("organizations")
        .select("*")
        .eq("id", profile.org_id)
        .single()

      if (orgError || !orgData) {
        setError("Your organization could not be loaded.")
        setLoading(false)
        return
      }

      setOrg(orgData)
      setLoading(false)
    }

    loadAppContext()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_OUT") {
        router.replace("/login")
      }
    })

    return () => subscription.unsubscribe()
  }, [router])

  if (loading) {
    return <LoadingScreen />
  }

  if (error) {
    return (
      <div className="p-6">
        <h1 className="text-lg font-semibold">
          Account setup issue
        </h1>

        <p className="mt-2 text-sm">
          {error}
        </p>
      </div>
    )
  }

  if (!org) {
    return null
  }

  return (
    <OrgProvider org={org}>
      {children}
    </OrgProvider>
  )
}