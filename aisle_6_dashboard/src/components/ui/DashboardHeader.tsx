"use client"

import { useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"
import { useOrg } from "@/components/OrgContext"
import KeheUploadCard from "@/components/ui/DistributorDataUploadCard"
import {
  Menu,
  BarChart3,
  MapPin,
  CalendarDays,
  Lightbulb,
} from "lucide-react"

type DashboardPage = "insights" | "dashboard" | "stores"

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
  {
    label: "Insights",
    value: "insights",
    href: "/deep-dive",
    icon: Lightbulb,
  },
  {
    label: "Dashboard",
    value: "dashboard",
    href: "/",
    icon: BarChart3,
  },
  {
    label: "Stores",
    value: "stores",
    href: "/store_health",
    icon: MapPin,
  },
] as const

export default function DashboardHeader({
  subtitle = "Sales Dashboard",
  dataThrough,
  isStale = false,
  activePage,
  onDataRefresh,
}: DashboardHeaderProps) {
  const router = useRouter()
  const { org } = useOrg()

  const theme = {
    ...DEFAULT_THEME,
    primary_color:
      org?.primary_color || DEFAULT_THEME.primary_color,
    secondary_color:
      org?.secondary_color || DEFAULT_THEME.secondary_color,
    accent_color:
      org?.accent_color || DEFAULT_THEME.accent_color,
  }

  const [menuOpen, setMenuOpen] = useState(false)
  const [dataModalOpen, setDataModalOpen] = useState(false)
  const [isRefreshingUnfi, setIsRefreshingUnfi] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState("")

  const [exportModalOpen, setExportModalOpen] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [exportMessage, setExportMessage] = useState("")

  if (!org) return null

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

      setExportMessage(
        "Export complete. Your AI-ready files have been downloaded."
      )
    } catch (err) {
      console.error("Export failed:", err)
      setExportMessage("Export failed. Please try again.")
    } finally {
      setIsExporting(false)
    }
  }

  const handleStoreListDownload = async () => {
    if (!API_BASE_URL || !org?.id) return

    setMenuOpen(false)

    try {
      const res = await fetch(
        `${API_BASE_URL}/exports/store_list?org_id=${org.id}`
      )

      if (!res.ok) {
        throw new Error("Store list download failed.")
      }

      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")

      a.href = url
      a.download = "store_list.csv"

      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error("Store list download failed:", err)
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
        err instanceof Error
          ? err.message
          : "Something went wrong refreshing UNFI."
      )
    } finally {
      setIsRefreshingUnfi(false)
    }
  }

  return (
    <>
      {/* ============================================================
          HEADER
      ============================================================ */}
      <header>
        <div className="flex min-h-[102px] items-center justify-between gap-8">
          {/* LEFT — BRAND */}
          <div className="flex shrink-0 items-center">
            {org.logo_display === "both" &&
            org.logo_mark_url &&
            org.logo_wordmark_url ? (
              <div className="flex items-center gap-3">
                <img
                  src={org.logo_mark_url}
                  alt=""
                  className="h-[40px] w-auto object-contain"
                />

                <img
                  src={org.logo_wordmark_url}
                  alt={org.name}
                  className="h-[36px] w-auto max-w-[220px] object-contain"
                />
              </div>
            ) : org.logo_display === "mark" && org.logo_mark_url ? (
              <img
                src={org.logo_mark_url}
                alt={org.name}
                className="h-[40px] w-auto object-contain"
              />
            ) : org.logo_display === "wordmark" && org.logo_wordmark_url ? (
              <img
                src={org.logo_wordmark_url}
                alt={org.name}
                className="h-[34px] w-auto max-w-[240px] object-contain"
              />
            ) : (
              <span
                className="text-[22px] font-semibold tracking-[-0.02em]"
                style={{ color: theme.charcoal }}
              >
                {org.name}
              </span>
            )}
          </div>

          {/* RIGHT SIDE */}
          <div className="flex min-w-0 items-center gap-5">
            {/* ======================================================
                PRIMARY NAV
            ====================================================== */}
            <nav className="flex items-center rounded-[22px] bg-[#F1ECE2] p-1.5">
              {pages.map((page) => {
                const isActive = activePage === page.value
                const Icon = page.icon
                const href =
                  page.value === "insights" &&
                  org.id === "839a67d6-7afa-4607-8524-8621184bfabc"
                    ? "/email_preview"
                    : page.href

                return (
                  <Link
                    key={page.value}
                    href={href}
                    className={`
                      relative flex h-[46px] items-center gap-2.5
                      rounded-[17px] px-5
                      text-[14px] font-medium
                      transition-all duration-200
                      ${
                        isActive
                          ? "bg-white shadow-[0_1px_3px_rgba(52,51,50,0.10)]"
                          : "hover:bg-white/45"
                      }
                    `}
                    style={{
                      color: isActive
                        ? theme.charcoal
                        : theme.muted,
                    }}
                  >
                    <Icon
                      className="h-[18px] w-[18px]"
                      strokeWidth={isActive ? 2 : 1.8}
                      style={{
                        color: isActive
                          ? theme.primary_color
                          : theme.muted,
                      }}
                    />

                    <span>{page.label}</span>

                  </Link>
                )
              })}
            </nav>

            {/* ======================================================
                DATE + DATA STATUS
            ====================================================== */}
            <div className="flex h-[46px] items-center gap-3 rounded-[17px] border border-[#DED4C4] bg-[#FBF8F2] px-4">
              {dataThrough && (
                <>
                  <CalendarDays
                    className="h-[17px] w-[17px]"
                    strokeWidth={1.8}
                    style={{ color: theme.muted }}
                  />

                  <span
                    className="whitespace-nowrap text-[14px] font-medium"
                    style={{ color: theme.charcoal }}
                  >
                    {dataThrough}
                  </span>

                  <div className="h-5 w-px bg-[#DED4C4]" />
                </>
              )}

              <span
                className="flex whitespace-nowrap items-center gap-2 rounded-full px-3 py-1.5 text-[12px] font-medium"
                style={{
                  backgroundColor: isStale
                    ? theme.yellowBg
                    : theme.greenBg,
                  color: isStale
                    ? theme.yellowText
                    : theme.greenText,
                }}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{
                    backgroundColor: isStale
                      ? "#F59E0B"
                      : "#16A34A",
                  }}
                />

                {isStale ? "Outdated" : "Up to date"}
              </span>
            </div>

            {/* ======================================================
                MENU
            ====================================================== */}
            <div className="relative">
              <button
                type="button"
                aria-label="Open menu"
                onClick={() => setMenuOpen((prev) => !prev)}
                className="
                  flex h-[46px] w-[46px]
                  items-center justify-center
                  rounded-[17px]
                  border border-[#DED4C4]
                  bg-[#F6F1E8]
                  transition-colors
                  hover:bg-[#EFE9DE]
                "
                style={{ color: theme.muted }}
              >
                <Menu className="h-5 w-5" strokeWidth={1.8} />
              </button>

              {menuOpen && (
                <div className="absolute right-0 top-[54px] z-50 w-56 overflow-hidden rounded-2xl border border-[#E5DDD0] bg-white shadow-[0_12px_30px_rgba(52,51,50,0.12)]">
                  <button
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
                    onClick={handleStoreListDownload}
                    className="w-full border-t px-4 py-3 text-left text-sm hover:bg-neutral-50"
                    style={{
                      color: theme.charcoal,
                      borderColor: theme.line,
                    }}
                  >
                    Download Store List
                  </button>

                  <button
                    onClick={handleSignOut}
                    className="w-full border-t px-4 py-3 text-left text-sm hover:bg-neutral-50"
                    style={{
                      color: theme.muted,
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

        {/* subtle bottom divider */}
        <div
          className="h-px w-full"
          style={{ backgroundColor: theme.line }}
        />
      </header>

      {/* ============================================================
          EXPORT MODAL
      ============================================================ */}
      {exportModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 px-4">
          <div className="w-full max-w-md rounded-[28px] border border-[#E5DDD0] bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2
                  className="text-xl font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  Export for AI
                </h2>

                <p
                  className="mt-1 text-sm"
                  style={{ color: theme.muted }}
                >
                  Preparing clean CSV files for analysis.
                </p>
              </div>

              <button
                onClick={() => setExportModalOpen(false)}
                disabled={isExporting}
                className="rounded-full bg-[#F3EEE6] px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
                style={{ color: theme.muted }}
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

                <p
                  className="text-sm font-medium"
                  style={{ color: theme.charcoal }}
                >
                  {exportMessage}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================
          DATA MODAL
      ============================================================ */}
      {dataModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 px-4">
          <div className="w-full max-w-3xl rounded-[28px] border border-[#E5DDD0] bg-white p-6 shadow-xl">
            <div className="mb-5 flex items-start justify-between">
              <div>
                <h2
                  className="text-xl font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  Update data
                </h2>

                <p
                  className="mt-1 text-sm"
                  style={{ color: theme.muted }}
                >
                  Upload KeHE or refresh UNFI.
                </p>
              </div>

              <button
                onClick={() => setDataModalOpen(false)}
                className="rounded-full bg-[#F3EEE6] px-3 py-1 text-sm"
                style={{ color: theme.muted }}
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

                    <p
                      className="text-sm"
                      style={{ color: theme.muted }}
                    >
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
                        {isRefreshingUnfi
                          ? "Refreshing..."
                          : "Refresh"}
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
