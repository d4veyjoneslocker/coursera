"use client"

import { useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { useOrg } from "@/components/OrgContext"
import KeheUploadCard from "@/components/ui/DistributorDataUploadCard"

type DashboardPage = "overview" | "store-health"

type DashboardHeaderProps = {
  brandName: string
  subtitle?: string
  logoSrc?: string
  lastUpdated?: string
  dataThrough?: string
  isStale?: boolean
  activePage: DashboardPage
  onDataRefresh?: () => Promise<void> | void
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

const theme = {
  blue: "#92B9DC",
  brown: "#705C4F",
  charcoal: "#343332",
  line: "#E5DDD0",
  muted: "#7A746B",
  greenBg: "#EAF6EE",
  greenText: "#2E7D32",
  yellowBg: "#FFF4E5",
  yellowText: "#A15C00",
}

const pages = [
  { label: "Overview", value: "overview", href: "/" },
  { label: "Store Health", value: "store-health", href: "/store_health" },
]

export default function DashboardHeader({
  brandName,
  subtitle = "Sales Dashboard",
  logoSrc,
  lastUpdated,
  dataThrough,
  isStale = false,
  activePage,
  onDataRefresh,
}: DashboardHeaderProps) {
  const router = useRouter()
  const org = useOrg()

  const [menuOpen, setMenuOpen] = useState(false)
  const [dataModalOpen, setDataModalOpen] = useState(false)
  const [isRefreshingUnfi, setIsRefreshingUnfi] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState("")

  const handleSignOut = async () => {
    await supabase.auth.signOut()
    router.push("/login")
  }

  const handleRefreshUnfi = async () => {
    if (!API_BASE_URL) return

    setIsRefreshingUnfi(true)
    setRefreshMessage("")

    try {
      const res = await fetch(
        `${API_BASE_URL}/distributors/unfi/refresh?org_id=${org.id}`,
        { method: "POST" }
      )

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || "UNFI refresh failed.")
      }

      setRefreshMessage("UNFI refreshed successfully.")
      await onDataRefresh?.()
    } catch (err) {
      setRefreshMessage(
        err instanceof Error ? err.message : "Something went wrong refreshing UNFI."
      )
    } finally {
      setIsRefreshingUnfi(false)
    }
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          {/* LEFT SIDE */}
          <div className="flex items-center gap-3">
            {logoSrc ? (
              <Image
                src={logoSrc}
                alt={`${brandName} logo`}
                width={48}
                height={48}
                className="h-12 w-auto object-contain"
              />
            ) : (
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#F3EEE6]">
                <span className="text-base font-semibold" style={{ color: theme.charcoal }}>
                  {brandName.slice(0, 2).toUpperCase()}
                </span>
              </div>
            )}

            <div>
              <h1
                className="text-[28px] font-semibold leading-none tracking-tight"
                style={{ color: theme.charcoal }}
              >
                {brandName}
              </h1>

              <p className="mt-1 text-[12px] uppercase tracking-[0.18em]" style={{ color: theme.muted }}>
                {subtitle}
              </p>
            </div>
          </div>

          {/* RIGHT SIDE */}
          <div className="flex items-center gap-6">
            <div
              className="inline-flex items-center rounded-full border p-1.5"
              style={{
                borderColor: "#D8CFBF",
                backgroundColor: "#F6F1E8",
              }}
            >
              {pages.map((page) => {
                const isActive = activePage === page.value

                return (
                  <Link
                    key={page.value}
                    href={page.href}
                    className="group relative rounded-full px-5 py-2.5 text-[13px] font-medium transition-all duration-200"
                    style={{
                      backgroundColor: isActive ? `${theme.blue}15` : "transparent",
                      color: isActive ? theme.charcoal : theme.brown,
                      boxShadow: isActive
                        ? "0 1px 2px rgba(52,51,50,0.08), inset 0 0 0 1px #E5DDD0"
                        : "none",
                    }}
                  >
                    <span className="relative z-10">{page.label}</span>

                    {!isActive && (
                      <span
                        className="absolute inset-0 rounded-full opacity-0 transition-all duration-200 group-hover:opacity-100"
                        style={{ backgroundColor: `${theme.brown}15` }}
                      />
                    )}

                    <span
                      className="absolute bottom-1.5 left-4 right-4 h-[2px] rounded-full transition-all duration-200"
                      style={{
                        backgroundColor: theme.blue,
                        opacity: isActive ? 1 : 0,
                      }}
                    />
                  </Link>
                )
              })}
            </div>

            <div className="flex items-center gap-4">
              <div className="flex flex-col items-end text-right">
                {dataThrough && (
                  <p className="text-xs font-medium" style={{ color: theme.charcoal }}>
                    Data through {dataThrough}
                  </p>
                )}

                {lastUpdated && (
                  <p className="mt-0.5 text-[11px]" style={{ color: theme.muted }}>
                    Updated {lastUpdated}
                  </p>
                )}

                <div
                  className="mt-1 inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-medium"
                  style={{
                    backgroundColor: isStale ? theme.yellowBg : theme.greenBg,
                    color: isStale ? theme.yellowText : theme.greenText,
                  }}
                >
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: isStale ? "#F59E0B" : "#16A34A" }}
                  />
                  {isStale ? "Data may be outdated" : "Data up to date"}
                </div>
              </div>

              {/* MENU */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setMenuOpen((prev) => !prev)}
                  className="rounded-full px-4 py-2 text-[12px] font-medium transition-all"
                  style={{
                    backgroundColor: "#F3EEE6",
                    border: "1px solid #D8CFBF",
                    color: theme.brown,
                  }}
                >
                  Menu
                </button>

                {menuOpen && (
                  <div
                    className="absolute right-0 top-11 z-50 w-52 overflow-hidden rounded-2xl border bg-white shadow-lg"
                    style={{ borderColor: theme.line }}
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setMenuOpen(false)
                        setDataModalOpen(true)
                      }}
                      className="w-full px-4 py-3 text-left text-sm hover:bg-neutral-50"
                      style={{ color: theme.charcoal }}
                    >
                      Upload / refresh data
                    </button>

                    <button
                      type="button"
                      onClick={handleSignOut}
                      className="w-full border-t px-4 py-3 text-left text-sm hover:bg-neutral-50"
                      style={{
                        color: theme.brown,
                        borderColor: theme.line,
                      }}
                    >
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="h-[1px] w-full" style={{ backgroundColor: theme.line }} />
      </div>

      {/* DATA MODAL */}
      {dataModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 px-4">
          <div
            className="w-full max-w-3xl rounded-[28px] border bg-white p-6 shadow-xl"
            style={{ borderColor: theme.line }}
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold" style={{ color: theme.charcoal }}>
                  Upload / refresh data
                </h2>
                <p className="mt-1 text-sm" style={{ color: theme.muted }}>
                  Upload a KeHE report or refresh UNFI data for this organization.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setDataModalOpen(false)}
                className="rounded-full px-3 py-1 text-sm"
                style={{
                  backgroundColor: "#F3EEE6",
                  color: theme.brown,
                }}
              >
                Close
              </button>
            </div>

            {API_BASE_URL && (
              <KeheUploadCard
                apiBaseUrl={API_BASE_URL}
                onUploadSuccess={async () => {
                  await onDataRefresh?.()
                }}
              />
            )}

            <div
              className="mt-4 rounded-2xl border p-5"
              style={{
                borderColor: theme.line,
                backgroundColor: "#F8F4EC",
              }}
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-semibold" style={{ color: theme.charcoal }}>
                    Refresh UNFI data
                  </h3>
                  <p className="mt-1 text-sm" style={{ color: theme.muted }}>
                    Pull the latest UNFI data and rebuild dashboard tables.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleRefreshUnfi}
                  disabled={isRefreshingUnfi}
                  className="rounded-xl px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                  style={{
                    backgroundColor: theme.blue,
                    color: theme.charcoal,
                  }}
                >
                  {isRefreshingUnfi ? "Refreshing..." : "Refresh UNFI"}
                </button>
              </div>

              {refreshMessage && (
                <p className="mt-3 text-sm" style={{ color: theme.brown }}>
                  {refreshMessage}
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}