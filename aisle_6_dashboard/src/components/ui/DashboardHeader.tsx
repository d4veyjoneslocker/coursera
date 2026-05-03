"use client"

import { useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { useOrg } from "@/components/OrgContext"
import KeheUploadCard from "@/components/ui/DistributorDataUploadCard"
import { Menu, BarChart3, Store, CalendarDays } from "lucide-react"

type DashboardPage = "overview" | "store-health"

type DashboardHeaderProps = {
  subtitle?: string
  dataThrough?: string
  isStale?: boolean
  activePage: DashboardPage
  onDataRefresh?: () => Promise<void> | void
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

const DEFAULT_THEME = {
  primary_color: "#9A93B0",
  secondary_color: "#C58E82",
  accent_color: "#C8795A",
  charcoal: "#343332",
  line: "#E5DDD0",
  muted: "#7A746B",
  greenBg: "#EAF6EE",
  greenText: "#2E7D32",
  yellowBg: "#FFF4E5",
  yellowText: "#A15C00",
}

const pages = [
  { label: "Overview", value: "overview", href: "/", icon: BarChart3 },
  { label: "Store Health", value: "store-health", href: "/store_health", icon: Store },
]

export default function DashboardHeader({
  subtitle = "Sales Dashboard",
  dataThrough,
  isStale = false,
  activePage,
  onDataRefresh,
}: DashboardHeaderProps) {
  const router = useRouter()
  const {org, skuColors} = useOrg()

  const theme = {
    ...DEFAULT_THEME,
    primary_color: org?.primary_color || DEFAULT_THEME.primary_color,
    secondary_color: org?.secondary_color || DEFAULT_THEME.secondary_color,
    accent_color: org?.accent_color || DEFAULT_THEME.accent_color,
  }

  const [menuOpen, setMenuOpen] = useState(false)
  const [dataModalOpen, setDataModalOpen] = useState(false)
  const [isRefreshingUnfi, setIsRefreshingUnfi] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState("")

  const [exportModalOpen, setExportModalOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [exportMessage, setExportMessage] = useState("")

  if (!org) return null

  const lastUpdated = org.last_refreshed_at
    ? new Date(org.last_refreshed_at).toLocaleString("en-US", {
        month: "long",
        year: "numeric",
      })
    : undefined


  const handleSignOut = async () => {
    await supabase.auth.signOut()
    router.push("/login")
  }

  const handleExport = async () => {
    if (!API_BASE_URL || !org?.id) return

    setMenuOpen(false)
    setExportModalOpen(true)
    setIsExporting(true)
    setExportMessage("Preparing your AI export...")

    try {
      const res = await fetch(
        `${API_BASE_URL}/exports/ai_package?org_id=${org.id}`
      )

      if (!res.ok) {
        throw new Error("Export failed.")
      }

      const blob = await res.blob()

      const orgName = org.name
        ? org.name
            .toLowerCase()
            .replace(/[^a-z0-9\s-]/g, "")
            .trim()
            .replace(/\s+/g, "-")
        : "org"

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")

      a.href = url
      a.download = `skuba-${orgName}-ai-export.zip`

      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)

      setExportMessage("Export complete. Your AI-ready files have been downloaded.")
    } catch (err) {
      console.error("Export failed:", err)
      setExportMessage("Export failed. Please try again.")
    } finally {
      setIsExporting(false)
    }
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
          {/* LEFT */}
          <div className="flex items-center gap-4">
            {org.logo_url ? (
              <Image
                src={org.logo_url}
                alt={`${org.name} logo`}
                width={48}
                height={48}
                className="h-12 w-auto object-contain"
              />
            ) : (
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#F3EEE6]">
                <span className="text-sm font-semibold text-[#343332]">
                  {org.name?.slice(0, 2).toUpperCase() || "EN"}
                </span>
              </div>
            )}

            <div>
              <h1 className="text-[28px] font-semibold leading-none tracking-tight text-[#343332]">
                {org.name}
              </h1>
              <p className="mt-1 text-[12px] uppercase tracking-[0.18em] text-[#7A746B]">
                {subtitle}
              </p>
            </div>
          </div>

          {/* RIGHT */}
          <div className="flex items-center gap-6">
            {/* NAV */}
            <div className="flex items-center rounded-full border border-[#D8CFBF] bg-[#F6F1E8] p-1.5">
              {pages.map((page) => {
                const isActive = activePage === page.value
                const Icon = page.icon

                return (
                  <Link
                    key={page.value}
                    href={page.href}
                    className="group relative flex items-center gap-2 rounded-full px-5 py-2.5 text-[13px] font-medium transition-all duration-200"
                    style={{
                      backgroundColor: isActive ? `${theme.primary_color}15` : "transparent",
                      color: isActive ? theme.charcoal : theme.accent_color,
                      boxShadow: isActive
                        ? "0 1px 2px rgba(52,51,50,0.08), inset 0 0 0 1px #E5DDD0"
                        : "none",
                    }}
                  >
                    <Icon className="h-4 w-4" />
                    {page.label}

                    {!isActive && (
                      <span
                        className="absolute inset-0 rounded-full opacity-0 transition-all duration-200 group-hover:opacity-100"
                        style={{ backgroundColor: `${theme.accent_color}15` }}
                      />
                    )}

                    <span
                      className="absolute bottom-1.5 left-4 right-4 h-[2px] rounded-full transition-all duration-200"
                      style={{
                        backgroundColor: theme.primary_color,
                        opacity: isActive ? 1 : 0,
                      }}
                    />
                  </Link>
                )
              })}
            </div>

            {/* DATA + STATUS */}
            <div className="flex items-center gap-3 rounded-full border border-[#D8CFBF] bg-[#FBF8F2] px-4 py-2">
              {dataThrough && (
                <>
                  <CalendarDays className="h-4 w-4 text-[#705C4F]" />
                  <span className="text-sm font-medium text-[#343332]">
                    {dataThrough}
                  </span>
                </>
              )}

              {lastUpdated && (
                <>
                  <span className="text-xs text-[#7A746B]">
                    Updated {lastUpdated}
                  </span>
                </>
              )}

              <div className="h-4 w-px bg-[#DED4C4]" />

              <span
                className="flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium"
                style={{
                  backgroundColor: isStale ? theme.yellowBg : theme.greenBg,
                  color: isStale ? theme.yellowText : theme.greenText,
                }}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: isStale ? "#F59E0B" : "#16A34A" }}
                />
                {isStale ? "Outdated" : "Up to date"}
              </span>
            </div>

            {/* MENU */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setMenuOpen((prev) => !prev)}
                className="flex items-center gap-2 rounded-full border border-[#D8CFBF] bg-[#F3EEE6] px-4 py-2 text-sm font-medium text-[#705C4F]"
              >
                <Menu className="h-4 w-4" />
                Menu
              </button>

              {menuOpen && (
                <div className="absolute right-0 top-11 z-50 w-52 overflow-hidden rounded-2xl border bg-white shadow-lg border-[#E5DDD0]">
                  <button
                    onClick={() => {
                      setMenuOpen(false)
                      setDataModalOpen(true)
                    }}
                    className="w-full px-4 py-3 text-left text-sm hover:bg-neutral-50"
                  >
                    Upload / refresh data
                  </button>

                  <button
                    onClick={handleExport}
                    className="w-full border-t px-4 py-3 text-left text-sm hover:bg-neutral-50"
                    style={{
                      color: theme.charcoal,
                      borderColor: theme.line,
                    }}
                  >
                    Export for AI
                  </button>

                  <button
                    onClick={handleSignOut}
                    className="w-full border-t border-[#E5DDD0] px-4 py-3 text-left text-sm hover:bg-neutral-50 text-[#705C4F]"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="h-[1px] w-full bg-[#E5DDD0]" />
      </div>

      {/* MODAL (unchanged) */}

      {/* EXPORT MODAL */}
      {exportModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 px-4">
          <div className="w-full max-w-md rounded-[28px] border bg-white p-6 shadow-xl border-[#E5DDD0]">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-[#343332]">
                  Export for AI
                </h2>
                <p className="mt-1 text-sm text-[#7A746B]">
                  Preparing clean CSV files for analysis.
                </p>
              </div>

              <button
                onClick={() => setExportModalOpen(false)}
                disabled={isExporting}
                className="rounded-full px-3 py-1 text-sm bg-[#F3EEE6] text-[#705C4F] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Close
              </button>
            </div>

            <div
              className="rounded-2xl border p-5"
              style={{
                borderColor: theme.line,
                backgroundColor: "#F8F4EC",
              }}
            >
              <div className="flex items-center gap-3">
                {isExporting && (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#D8CFBF] border-t-[#705C4F]" />
                )}

                <p className="text-sm font-medium text-[#343332]">
                  {exportMessage}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DATA MODAL */}
      {dataModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 px-4">
          <div className="w-full max-w-3xl rounded-[28px] border bg-white p-6 shadow-xl border-[#E5DDD0]">
            <div className="mb-5 flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold text-[#343332]">
                  Update data
                </h2>
                <p className="mt-1 text-sm text-[#7A746B]">
                  Upload KeHE or refresh UNfI.
                </p>
              </div>

              <button
                onClick={() => setDataModalOpen(false)}
                className="rounded-full px-3 py-1 text-sm bg-[#F3EEE6] text-[#705C4F]"
              >
                Close
              </button>
            </div>

            <div className="grid gap-4">
              {API_BASE_URL && (
                <KeheUploadCard
                  apiBaseUrl={API_BASE_URL}
                  onUploadSuccess={async () => {
                    await onDataRefresh?.()
                  }}
                />
              )}

              <div
                className="rounded-2xl border p-5 shadow-sm"
                style={{
                  borderColor: theme.line,
                  backgroundColor: "white",
                }}
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                  <div className="space-y-1">
                    <p
                      className="text-[12px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: theme.muted }}
                    >
                      Data Refresh
                    </p>

                    <h3
                      className="text-lg font-semibold"
                      style={{ color: theme.charcoal }}
                    >
                      Refresh UNFI Data
                    </h3>

                    <p className="text-sm" style={{ color: theme.muted }}>
                      Automatically pull the latest UNFI data from Crisp.
                    </p>
                  </div>

                  <div className="flex w-full flex-col gap-3 md:w-auto md:min-w-[420px]">
                    <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
                      <button
                        type="button"
                        onClick={handleRefreshUnfi}
                        disabled={isRefreshingUnfi}
                        className="rounded-xl px-4 py-2 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
                        style={{
                          backgroundColor: theme.primary_color,
                          color: theme.charcoal,
                        }}
                      >
                        {isRefreshingUnfi ? "Refreshing..." : "Refresh"}
                      </button>
                    </div>

                    {refreshMessage && (
                      <div
                        className="rounded-xl px-3 py-2 text-sm font-medium"
                        style={{
                          backgroundColor: theme.greenBg,
                          color: theme.greenText,
                        }}
                      >
                        {refreshMessage}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}