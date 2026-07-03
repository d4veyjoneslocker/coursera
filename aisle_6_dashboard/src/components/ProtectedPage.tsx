"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { OrgProvider, type Org } from "@/components/OrgContext"
import KeheUploadCard from "@/components/ui/DistributorDataUploadCard"
import LoadingScreen from "@/components/LoadingScreen"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

export default function ProtectedPage({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [org, setOrg] = useState<Org | null>(null)
  const [hasData, setHasData] = useState<boolean | null>(null)

  const loadDataStatus = async (orgId: string) => {
    if (!API_BASE_URL) return

    const res = await fetch(
      `${API_BASE_URL}/distributors/kehe/status?org_id=${orgId}`
    )

    const data = await res.json()
    setHasData(data.status === "ready")
  }

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
        setError("Your account exists, but it is not linked to an organization yet.")
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

      await loadDataStatus(orgData.id)

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
        <h1 className="text-lg font-semibold">Account setup issue</h1>
        <p className="mt-2 text-sm">{error}</p>
      </div>
    )
  }

  if (!org) return null

  if (hasData === false) {
    return (
      <OrgProvider org={org}>
        <main className="min-h-screen p-8" style={{ backgroundColor: "#F7F3E8" }}>
          <div className="mx-auto max-w-4xl space-y-6">
            <div
              className="rounded-2xl border p-10 text-center"
              style={{
                borderColor: "#E5DDD0",
                backgroundColor: "#F8F4EC",
              }}
            >
              <h2 className="mb-2 text-lg font-semibold" style={{ color: "#343332" }}>
                No data yet
              </h2>
              <p className="text-sm" style={{ color: "#7A746B" }}>
                Upload your KeHE report to start building your dashboard.
              </p>
            </div>

            {API_BASE_URL && (
              <KeheUploadCard
                apiBaseUrl={API_BASE_URL}
                onUploadSuccess={async () => {
                  await loadDataStatus(org.id)
                }}
              />
            )}
          </div>
        </main>
      </OrgProvider>
    )
  }

  return <OrgProvider org={org}>{children}</OrgProvider>
}