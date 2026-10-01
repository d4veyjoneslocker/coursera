"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  Lightbulb,
  ChartBar,
  Storefront,
  Package,
  Warehouse,
  Export,
  ListBullets,
  UploadSimple,
  SignOut,
  CalendarBlank,
  X,
} from "@phosphor-icons/react"

import { supabase } from "@/lib/supabase"
import { useOrg } from "@/components/OrgContext"
import DistributorDataUploadCard from "@/components/ui/DistributorDataUploadCard"


type DashboardPage =
  | "insights"
  | "dashboard"
  | "stores"
  | "inventory"
  | "inventory-dashboard"


type DashboardHeaderProps = {
  subtitle?: string
  dataThrough?: string
  isStale?: boolean
  activePage: DashboardPage
  onDataRefresh?: () => Promise<void> | void
}


const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL


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


const salesPages = [
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
    icon: ChartBar,
  },
  {
    label: "Stores",
    value: "stores",
    href: "/store_health",
    icon: Storefront,
  },
] as const


const operationsPages = [
  {
    label: "Inventory Planning",
    value: "inventory",
    href: "/inventory",
    icon: Package,
  },
  {
    label: "Inventory Dashboard",
    value: "inventory-dashboard",
    href: "/inventory/dcs",
    icon: Warehouse,
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
      org?.primary_color ||
      DEFAULT_THEME.primary_color,

    secondary_color:
      org?.secondary_color ||
      DEFAULT_THEME.secondary_color,

    accent_color:
      org?.accent_color ||
      DEFAULT_THEME.accent_color,
  }


  const [
    dataModalOpen,
    setDataModalOpen,
  ] = useState(false)

  const [
    isRefreshingUnfi,
    setIsRefreshingUnfi,
  ] = useState(false)

  const [
    refreshMessage,
    setRefreshMessage,
  ] = useState("")

  const [
    exportModalOpen,
    setExportModalOpen,
  ] = useState(false)

  const [
    isExporting,
    setIsExporting,
  ] = useState(false)

  const [
    exportMessage,
    setExportMessage,
  ] = useState("")


  if (!org) return null


  /* ============================================================
     SIGN OUT
  ============================================================ */

  const handleSignOut = async () => {

    await supabase.auth.signOut()

    router.push("/login")
  }


  /* ============================================================
     AI EXPORT
  ============================================================ */

  const handleExport = async () => {

    if (!API_BASE_URL || !org?.id) {
      return
    }


    setExportModalOpen(true)

    setIsExporting(true)

    setExportMessage(
      "Preparing your AI export..."
    )


    try {

      const res = await fetch(
        `${API_BASE_URL}/exports/ai_package?org_id=${org.id}`
      )


      if (!res.ok) {
        throw new Error(
          "Export failed."
        )
      }


      const blob = await res.blob()


      const orgName = org.name
        ? org.name
            .toLowerCase()
            .replace(
              /[^a-z0-9\s-]/g,
              ""
            )
            .trim()
            .replace(/\s+/g, "-")
        : "org"


      const url =
        window.URL.createObjectURL(
          blob
        )


      const a =
        document.createElement("a")


      a.href = url

      a.download =
        `skuba-${orgName}-ai-export.zip`


      document.body.appendChild(a)

      a.click()

      a.remove()


      window.URL.revokeObjectURL(
        url
      )


      setExportMessage(
        "Export complete. Your AI-ready files have been downloaded."
      )

    } catch (err) {

      console.error(
        "Export failed:",
        err
      )


      setExportMessage(
        "Export failed. Please try again."
      )

    } finally {

      setIsExporting(false)
    }
  }


  /* ============================================================
     STORE LIST DOWNLOAD
  ============================================================ */

  const handleStoreListDownload =
    async () => {

      if (!API_BASE_URL || !org?.id) {
        return
      }


      try {

        const res = await fetch(
          `${API_BASE_URL}/exports/store_list?org_id=${org.id}`
        )


        if (!res.ok) {

          throw new Error(
            "Store list download failed."
          )
        }


        const blob =
          await res.blob()


        const url =
          window.URL.createObjectURL(
            blob
          )


        const a =
          document.createElement("a")


        a.href = url

        a.download =
          "store_list.csv"


        document.body.appendChild(a)

        a.click()

        a.remove()


        window.URL.revokeObjectURL(
          url
        )

      } catch (err) {

        console.error(
          "Store list download failed:",
          err
        )
      }
    }


  /* ============================================================
     UNFI REFRESH
  ============================================================ */

  const handleRefreshUnfi =
    async () => {

      if (!API_BASE_URL) {
        return
      }


      setIsRefreshingUnfi(true)

      setRefreshMessage("")


      try {

        const res = await fetch(
          `${API_BASE_URL}/distributors/unfi/refresh?org_id=${org.id}`,
          {
            method: "POST",
          }
        )


        const data =
          await res.json()


        if (!res.ok) {

          throw new Error(
            data.detail ||
              "UNFI refresh failed."
          )
        }


        setRefreshMessage(
          "UNFI refreshed successfully."
        )


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


  /* ============================================================
     SHARED SIDEBAR STYLES
  ============================================================ */

  const sectionLabelClass =
    "mb-2 px-3 text-[10px] font-semibold tracking-[0.18em]"

  const actionClass =
    "group flex h-[42px] w-full items-center gap-3 rounded-[12px] px-3 text-left text-[13px] font-medium transition-all duration-150 hover:bg-white/60"


  return (
    <>

      {/* ============================================================
          SIDEBAR
      ============================================================ */}

      <aside
        className="
          fixed
          inset-y-0
          left-0
          z-40
          flex
          w-[238px]
          flex-col
          border-r
          px-5
          pb-6
          pt-7
        "
        style={{
          backgroundColor: `${theme.primary_color}12`,
          borderColor: `${theme.primary_color}25`,
        }}
      >

        {/* ======================================================
            BRAND
        ====================================================== */}

        <div
          className="
            flex
            min-h-[62px]
            items-center
            px-2
          "
        >

          {org.logo_display === "both" &&
          org.logo_mark_url &&
          org.logo_wordmark_url ? (

            <div
              className="
                flex
                items-center
                gap-3
              "
            >

              <img
                src={org.logo_mark_url}
                alt=""
                className="
                  h-[36px]
                  w-auto
                  max-w-[42px]
                  object-contain
                "
              />

              <img
                src={org.logo_wordmark_url}
                alt={org.name}
                className="
                  h-[31px]
                  w-auto
                  max-w-[140px]
                  object-contain
                  object-left
                "
              />

            </div>

          ) : org.logo_display ===
              "mark" &&
            org.logo_mark_url ? (

            <img
              src={org.logo_mark_url}
              alt={org.name}
              className="
                h-[38px]
                w-auto
                max-w-[160px]
                object-contain
                object-left
              "
            />

          ) : org.logo_display ===
              "wordmark" &&
            org.logo_wordmark_url ? (

            <img
              src={org.logo_wordmark_url}
              alt={org.name}
              className="
                h-[32px]
                w-auto
                max-w-[175px]
                object-contain
                object-left
              "
            />

          ) : (

            <span
              className="
                truncate
                text-[20px]
                font-semibold
                tracking-[-0.02em]
              "
              style={{
                color:
                  theme.charcoal,
              }}
            >
              {org.name}
            </span>
          )}

        </div>


        {/* ======================================================
            NAVIGATION
        ====================================================== */}

        <nav
          className="
            mt-8
            flex-1
            overflow-y-auto
          "
        >

          {/* SALES */}

          <div
            className={sectionLabelClass}
            style={{
              color: `${theme.primary_color}CC`,
            }}
          >
            SALES
          </div>


          <div className="space-y-[3px]">

            {salesPages.map((page) => {

              const isActive =
                activePage === page.value

              const Icon = page.icon


              /*
               * Keep the demo-org Insights override.
               * This can diverge from the default route later
               * without changing the sidebar architecture.
               */
              const href =
                page.value === "insights" &&
                org.id ===
                  "839a67d6-7afa-4607-8524-8621184bfabc"
                  ? "/deep-dive"
                  : page.href


              return (

                <Link
                  key={page.value}
                  href={href}
                  className={`
                    group
                    flex
                    h-[44px]
                    w-full
                    items-center
                    gap-3
                    rounded-[12px]
                    px-3
                    text-[14px]
                    font-medium
                    transition-all
                    duration-150

                    ${
                      isActive
                        ? `
                            bg-white
                            shadow-[0_5px_15px_rgba(53,45,35,0.06)]
                          `
                        : `
                            hover:bg-white/60
                          `
                    }
                  `}
                  style={{
                    color:
                      isActive
                        ? theme.charcoal
                        : theme.muted,
                  }}
                >

                  <Icon
                    size={20}
                    weight={
                      isActive
                        ? "duotone"
                        : "regular"
                    }
                    color={
                      isActive
                        ? theme.primary_color
                        : theme.muted
                    }
                  />

                  <span>
                    {page.label}
                  </span>

                </Link>
              )
            })}

          </div>


          {/* OPERATIONS */}

          <div className="mt-8">

            <div
              className={sectionLabelClass}
              style={{
                color: `${theme.primary_color}CC`,
              }}
            >
              OPERATIONS
            </div>


            <div className="space-y-[3px]">

              {operationsPages.map((page) => {

                const isActive =
                  activePage === page.value

                const Icon = page.icon


                return (

                  <Link
                    key={page.value}
                    href={page.href}
                    className={`
                      group
                      flex
                      h-[44px]
                      w-full
                      items-center
                      gap-3
                      rounded-[12px]
                      px-3
                      text-[14px]
                      font-medium
                      transition-all
                      duration-150

                      ${
                        isActive
                          ? `
                              bg-white
                              shadow-[0_5px_15px_rgba(53,45,35,0.06)]
                            `
                          : `
                              hover:bg-white/60
                            `
                      }
                    `}
                    style={{
                      color:
                        isActive
                          ? theme.charcoal
                          : theme.muted,
                    }}
                  >

                    <Icon
                      size={20}
                      weight={
                        isActive
                          ? "duotone"
                          : "regular"
                      }
                      color={
                        isActive
                          ? theme.primary_color
                          : theme.muted
                      }
                    />

                    <span className="leading-tight">
                      {page.label}
                    </span>

                  </Link>
                )
              })}

            </div>

          </div>


          {/* DATA */}

          <div className="mt-8">

            <div
              className={sectionLabelClass}
              style={{
                color: `${theme.primary_color}CC`,
              }}
            >
              DATA
            </div>


            <div className="space-y-[3px]">

              <button
                type="button"
                onClick={handleExport}
                className={actionClass}
                style={{
                  color:
                    theme.muted,
                }}
              >

                <Export
                  size={19}
                  weight="regular"
                  color={theme.muted}
                />

                <span>
                  Export for AI
                </span>

              </button>


              <button
                type="button"
                onClick={
                  handleStoreListDownload
                }
                className={actionClass}
                style={{
                  color:
                    theme.muted,
                }}
              >

                <ListBullets
                  size={19}
                  weight="regular"
                  color={theme.muted}
                />

                <span>
                  Export Store List
                </span>

              </button>

            </div>

          </div>

        </nav>


        {/* ======================================================
            SIDEBAR BOTTOM
        ====================================================== */}

        <div
          className="
            border-t
            pt-4
          "
          style={{
            borderColor:
              `${theme.primary_color}25`,
          }}
        >

          {/* UPDATE DATA */}

          <button
            type="button"
            onClick={() => {
              setDataModalOpen(true)
            }}
            className={actionClass}
            style={{
              color:
                theme.muted,
            }}
          >

            <UploadSimple
              size={19}
              weight="regular"
              color={theme.muted}
            />

            Update data

          </button>


          {/* SIGN OUT */}

          <button
            type="button"
            onClick={handleSignOut}
            className={actionClass}
            style={{
              color:
                theme.muted,
            }}
          >

            <SignOut
              size={19}
              weight="regular"
              color={theme.muted}
            />

            Sign out

          </button>

        </div>

      </aside>


      {/* ============================================================
          DATE + DATA STATUS
      ============================================================ */}

      <div
        className="
          fixed
          right-10
          top-6
          z-30
          flex
          h-[46px]
          items-center
          gap-3
          rounded-[17px]
          border
          border-[#DED4C4]
          bg-[#FBF8F2]
          px-4
        "
      >

        {dataThrough && (
          <>

            <CalendarBlank
              size={18}
              weight="regular"
              color={theme.muted}
            />


            <span
              className="
                whitespace-nowrap
                text-[14px]
                font-medium
              "
              style={{
                color:
                  theme.charcoal,
              }}
            >
              {dataThrough}
            </span>


            <div
              className="
                h-5
                w-px
                bg-[#DED4C4]
              "
            />

          </>
        )}


        <span
          className="
            flex
            items-center
            gap-2
            whitespace-nowrap
            rounded-full
            px-3
            py-1.5
            text-[12px]
            font-medium
          "
          style={{
            backgroundColor:
              isStale
                ? theme.yellowBg
                : theme.greenBg,

            color:
              isStale
                ? theme.yellowText
                : theme.greenText,
          }}
        >

          <span
            className="
              h-2
              w-2
              rounded-full
            "
            style={{
              backgroundColor:
                isStale
                  ? "#F59E0B"
                  : "#16A34A",
            }}
          />

          {isStale
            ? "Outdated"
            : "Up to date"}

        </span>

      </div>


      {/* ============================================================
          EXPORT MODAL
      ============================================================ */}

      {exportModalOpen && (

        <div
          className="
            fixed
            inset-0
            z-[100]
            flex
            items-center
            justify-center
            bg-black/30
            px-4
          "
        >

          <div
            className="
              w-full
              max-w-md
              rounded-[28px]
              border
              border-[#E5DDD0]
              bg-white
              p-6
              shadow-xl
            "
          >

            <div
              className="
                mb-5
                flex
                items-start
                justify-between
                gap-4
              "
            >

              <div>

                <h2
                  className="
                    text-xl
                    font-semibold
                  "
                  style={{
                    color:
                      theme.charcoal,
                  }}
                >
                  Export for AI
                </h2>


                <p
                  className="
                    mt-1
                    text-sm
                  "
                  style={{
                    color:
                      theme.muted,
                  }}
                >
                  Preparing clean CSV
                  files for analysis.
                </p>

              </div>


              <button
                type="button"
                onClick={() =>
                  setExportModalOpen(
                    false
                  )
                }
                disabled={
                  isExporting
                }
                className="
                  flex
                  h-8
                  w-8
                  items-center
                  justify-center
                  rounded-full
                  bg-[#F3EEE6]
                  disabled:cursor-not-allowed
                  disabled:opacity-50
                "
                style={{
                  color:
                    theme.muted,
                }}
              >

                <X
                  size={16}
                  weight="bold"
                />

              </button>

            </div>


            <div
              className="
                rounded-2xl
                border
                p-5
              "
              style={{
                borderColor:
                  theme.line,

                backgroundColor:
                  "#F8F4EC",
              }}
            >

              <div
                className="
                  flex
                  items-center
                  gap-3
                "
              >

                {isExporting && (

                  <div
                    className="
                      h-4
                      w-4
                      animate-spin
                      rounded-full
                      border-2
                      border-[#D8CFBF]
                      border-t-[#705C4F]
                    "
                  />

                )}


                <p
                  className="
                    text-sm
                    font-medium
                  "
                  style={{
                    color:
                      theme.charcoal,
                  }}
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

        <div
          className="
            fixed
            inset-0
            z-[100]
            flex
            items-center
            justify-center
            bg-black/30
            px-4
          "
        >

          <div
            className="
              w-full
              max-w-3xl
              rounded-[28px]
              border
              border-[#E5DDD0]
              bg-white
              p-6
              shadow-xl
            "
          >

            {/* MODAL HEADER */}

            <div
              className="
                mb-5
                flex
                items-start
                justify-between
              "
            >

              <div>

                <h2
                  className="
                    text-xl
                    font-semibold
                  "
                  style={{
                    color:
                      theme.charcoal,
                  }}
                >
                  Update data
                </h2>


                <p
                  className="
                    mt-1
                    text-sm
                  "
                  style={{
                    color:
                      theme.muted,
                  }}
                >
                  Upload KeHE or refresh
                  UNFI.
                </p>

              </div>


              <button
                type="button"
                onClick={() =>
                  setDataModalOpen(
                    false
                  )
                }
                className="
                  flex
                  h-8
                  w-8
                  items-center
                  justify-center
                  rounded-full
                  bg-[#F3EEE6]
                "
                style={{
                  color:
                    theme.muted,
                }}
              >

                <X
                  size={16}
                  weight="bold"
                />

              </button>

            </div>


            <div className="grid gap-4">

              {/* KEHE UPLOAD */}

              {API_BASE_URL && (

                <DistributorDataUploadCard
                  distributor="kehe"
                  apiBaseUrl={
                    API_BASE_URL
                  }
                  uploadMode="standard"
                  onUploadSuccess={() => {
                    void onDataRefresh?.()
                  }}
                />

              )}


              {/* UNFI REFRESH */}

              <div
                className="
                  rounded-2xl
                  border
                  p-5
                  shadow-sm
                "
                style={{
                  borderColor:
                    theme.line,

                  backgroundColor:
                    "white",
                }}
              >

                <div
                  className="
                    flex
                    flex-col
                    gap-4
                    md:flex-row
                    md:items-end
                    md:justify-between
                  "
                >

                  <div className="space-y-1">

                    <p
                      className="
                        text-[12px]
                        font-semibold
                        uppercase
                        tracking-[0.16em]
                      "
                      style={{
                        color:
                          theme.muted,
                      }}
                    >
                      Data Refresh
                    </p>


                    <h3
                      className="
                        text-lg
                        font-semibold
                      "
                      style={{
                        color:
                          theme.charcoal,
                      }}
                    >
                      Refresh UNFI Data
                    </h3>


                    <p
                      className="
                        text-sm
                      "
                      style={{
                        color:
                          theme.muted,
                      }}
                    >
                      Automatically pull
                      the latest UNFI
                      data from Crisp.
                    </p>

                  </div>


                  <div
                    className="
                      flex
                      w-full
                      flex-col
                      gap-3
                      md:w-auto
                      md:min-w-[420px]
                    "
                  >

                    <div
                      className="
                        flex
                        flex-col
                        gap-3
                        sm:flex-row
                        sm:justify-end
                      "
                    >

                      <button
                        type="button"
                        onClick={
                          handleRefreshUnfi
                        }
                        disabled={
                          isRefreshingUnfi
                        }
                        className="
                          rounded-xl
                          px-4
                          py-2
                          text-sm
                          font-medium
                          transition-opacity
                          disabled:cursor-not-allowed
                          disabled:opacity-50
                        "
                        style={{
                          backgroundColor:
                            theme.primary_color,

                          color:
                            theme.charcoal,
                        }}
                      >

                        {isRefreshingUnfi
                          ? "Refreshing..."
                          : "Refresh"}

                      </button>

                    </div>


                    {refreshMessage && (

                      <div
                        className="
                          rounded-xl
                          px-3
                          py-2
                          text-sm
                          font-medium
                        "
                        style={{
                          backgroundColor:
                            theme.greenBg,

                          color:
                            theme.greenText,
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