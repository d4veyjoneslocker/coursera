"use client"

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"
import { useRouter } from "next/navigation"

import { useOrg } from "@/components/OrgContext"
import { supabase } from "@/lib/supabase"
import KeheUploadCard from "@/components/ui/DistributorDataUploadCard"

const theme = {
  bg: "#F7F3E8",
  surface: "#FFFDF8",
  gold: "#F7B045",
  brown: "#705C4F",
  charcoal: "#343332",
  line: "#D8CFB7",
  muted: "#8D857D",
}

type OrgDistributor = {
  distributor: string
  start_date: string | null
  is_supported: boolean
}

type MonthItem = {
  key: string
  label: string
  year: number
}

function getLastCompletedMonth() {
  const now = new Date()

  return new Date(
    now.getFullYear(),
    now.getMonth() - 1,
    1
  )
}

function monthToItem(date: Date): MonthItem {
  const year = date.getFullYear()
  const month = date.getMonth() + 1

  return {
    key: `${year}-${String(month).padStart(2, "0")}`,
    label: date.toLocaleString("en-US", {
      month: "short",
    }),
    year,
  }
}

function buildMonthsFromStart(
  startDate: string | null
): MonthItem[] {
  if (!startDate) return []

  const start = new Date(`${startDate}T00:00:00`)
  const end = getLastCompletedMonth()

  if (start > end) {
    return []
  }

  const months: MonthItem[] = []

  let current = new Date(
    start.getFullYear(),
    start.getMonth(),
    1
  )

  while (current <= end) {
    months.push(monthToItem(current))

    current = new Date(
      current.getFullYear(),
      current.getMonth() + 1,
      1
    )
  }

  return months
}

function buildTrailingMonths(count: number): MonthItem[] {
  const end = getLastCompletedMonth()

  const start = new Date(
    end.getFullYear(),
    end.getMonth() - (count - 1),
    1
  )

  const months: MonthItem[] = []

  let current = start

  while (current <= end) {
    months.push(monthToItem(current))

    current = new Date(
      current.getFullYear(),
      current.getMonth() + 1,
      1
    )
  }

  return months
}

function formatRange(months: MonthItem[]) {
  if (!months.length) return ""

  const first = months[0]
  const last = months[months.length - 1]

  return `${first.label} ${first.year} – ${last.label} ${last.year}`
}

export default function FreeTrialUploadPage() {
  const router = useRouter()
  const { org } = useOrg()

  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? ""

  const [distributors, setDistributors] = useState<
    OrgDistributor[]
  >([])

  const [
    uploadedKeheMonths,
    setUploadedKeheMonths,
  ] = useState<Set<string>>(new Set())

  const [loading, setLoading] = useState(true)

  const kehe = distributors.find(
    (row) =>
      row.distributor.toLowerCase() === "kehe"
  )

  const unfi = distributors.find(
    (row) =>
      row.distributor.toLowerCase() === "unfi"
  )

  /*
   * Complete history available since the brand
   * started working with KeHE.
   */
  const fullKeheHistory = useMemo(
    () =>
      buildMonthsFromStart(
        kehe?.start_date ?? null
      ),
    [kehe?.start_date]
  )

  const completedHistoryMonths =
    fullKeheHistory.length

  /*
   * A newer brand with fewer than 6 completed
   * months can run an analysis once all of its
   * history since launch has been uploaded.
   */
  const isNewBrand =
    completedHistoryMonths > 0 &&
    completedHistoryMonths < 6

  /*
   * Established brands specifically need the
   * latest 6 consecutive completed months.
   */
  const trailing6Months = useMemo(
    () => buildTrailingMonths(6),
    []
  )

  /*
   * 12 months unlocks the deeper history tier.
   */
  const trailing12Months = useMemo(
    () => buildTrailingMonths(12),
    []
  )

  /*
   * Months that are REQUIRED before the button
   * can unlock.
   */
  const requiredMonths = isNewBrand
    ? fullKeheHistory
    : trailing6Months

  const requiredUploadedCount =
    requiredMonths.filter((month) =>
      uploadedKeheMonths.has(month.key)
    ).length

  const hasAllRequiredMonths =
    requiredMonths.length > 0 &&
    requiredMonths.every((month) =>
      uploadedKeheMonths.has(month.key)
    )

  /*
   * The 12M tier is only truly available if
   * the brand itself has at least 12 completed
   * months of KeHE history.
   */
  const canPossiblyHave12Months =
    completedHistoryMonths >= 12

  const has12MonthHistory =
    canPossiblyHave12Months &&
    trailing12Months.every((month) =>
      uploadedKeheMonths.has(month.key)
    )

  const analysisTier = has12MonthHistory
    ? "12m"
    : hasAllRequiredMonths && isNewBrand
      ? "new_brand"
      : hasAllRequiredMonths
        ? "6m"
        : null

  const refreshKeheCoverage =
    useCallback(async () => {
      if (!org?.id) return

      const { data, error } = await supabase
        .from("org_distributor_months")
        .select("month")
        .eq("org_id", org.id)
        .eq("distributor", "kehe")
        .order("month")

      if (error) {
        console.error(
          "Failed to load KeHE coverage:",
          error
        )
        return
      }

      setUploadedKeheMonths(
        new Set(
          (data ?? []).map((row) =>
            row.month.slice(0, 7)
          )
        )
      )
    }, [org?.id])

  useEffect(() => {
    if (!org?.id) return

    async function loadPage() {
      setLoading(true)

      const { data, error } = await supabase
        .from("org_distributors")
        .select(
          "distributor, start_date, is_supported"
        )
        .eq("org_id", org!.id)

      if (error) {
        console.error(
          "Failed to load distributors:",
          error
        )

        setLoading(false)
        return
      }

      setDistributors(data ?? [])

      await refreshKeheCoverage()

      setLoading(false)
    }

    loadPage()
  }, [org?.id, refreshKeheCoverage])

  if (!org?.id || loading) {
    return (
      <main
        className="min-h-screen px-6 py-16"
        style={{
          background: theme.bg,
        }}
      >
        <div
          className="mx-auto max-w-5xl text-sm"
          style={{
            color: theme.brown,
          }}
        >
          Loading your upload setup...
        </div>
      </main>
    )
  }

  return (
    <main
      className="min-h-screen px-6 py-12 md:px-10"
      style={{
        background: theme.bg,
      }}
    >
      <div className="mx-auto max-w-5xl">

        {/* -----------------------------
            Header
        ----------------------------- */}

        <div className="mb-10">
          <p
            className="mb-3 text-sm font-medium"
            style={{
              color: theme.brown,
            }}
          >
            Your free analysis
          </p>

          <h1
            className="max-w-2xl text-4xl font-semibold tracking-tight md:text-5xl"
            style={{
              color: theme.charcoal,
            }}
          >
            Upload your distributor data.
          </h1>

          <p
            className="mt-4 max-w-2xl text-base leading-7"
            style={{
              color: theme.brown,
            }}
          >
            We&apos;ll use your historical
            distributor data to find the changes,
            risks, and opportunities worth your
            attention.
          </p>
        </div>

        <div className="space-y-6">

          {/* -----------------------------
              KeHE
          ----------------------------- */}

          {kehe && (
            <section
              className="border p-6 md:p-8"
              style={{
                background: theme.surface,
                borderColor: theme.line,
              }}
            >
              <div>
                <h2
                  className="text-2xl font-semibold"
                  style={{
                    color: theme.charcoal,
                  }}
                >
                  KeHE
                </h2>

                {isNewBrand ? (
                  <>
                    <p
                      className="mt-2 text-sm"
                      style={{
                        color: theme.brown,
                      }}
                    >
                      Because you started working
                      with KeHE recently, upload
                      your complete history to run
                      your analysis.
                    </p>

                    {requiredMonths.length > 0 && (
                      <p
                        className="mt-1 text-sm font-medium"
                        style={{
                          color: theme.charcoal,
                        }}
                      >
                        Required:{" "}
                        {formatRange(
                          requiredMonths
                        )}
                      </p>
                    )}
                  </>
                ) : (
                  <>
                    <p
                      className="mt-2 text-sm"
                      style={{
                        color: theme.brown,
                      }}
                    >
                      Upload the latest 6
                      completed months to run your
                      analysis.
                    </p>

                    <p
                      className="mt-1 text-sm font-medium"
                      style={{
                        color: theme.charcoal,
                      }}
                    >
                      Required:{" "}
                      {formatRange(requiredMonths)}
                    </p>
                  </>
                )}
              </div>

              {/* -----------------------------
                  Required month tracker
              ----------------------------- */}

              {requiredMonths.length > 0 && (
                <div className="mt-8">
                  <div className="grid grid-cols-3 gap-4 sm:grid-cols-6">
                    {requiredMonths.map(
                      (month) => {
                        const uploaded =
                          uploadedKeheMonths.has(
                            month.key
                          )

                        return (
                          <div
                            key={month.key}
                            className="flex flex-col items-center gap-2"
                          >
                            <span
                              className="text-xs font-medium"
                              style={{
                                color:
                                  theme.brown,
                              }}
                            >
                              {month.label}
                            </span>

                            <div
                              className="flex h-12 w-12 items-center justify-center border text-base font-semibold"
                              style={{
                                background:
                                  uploaded
                                    ? theme.gold
                                    : "transparent",

                                borderColor:
                                  uploaded
                                    ? theme.gold
                                    : theme.line,

                                color:
                                  uploaded
                                    ? theme.charcoal
                                    : theme.brown,
                              }}
                            >
                              {uploaded
                                ? "✓"
                                : ""}
                            </div>

                            <span
                              className="text-[10px]"
                              style={{
                                color:
                                  theme.muted,
                              }}
                            >
                              {month.year}
                            </span>
                          </div>
                        )
                      }
                    )}
                  </div>

                  <div className="mt-6">
                    {hasAllRequiredMonths ? (
                      <p
                        className="text-sm font-semibold"
                        style={{
                          color:
                            theme.charcoal,
                        }}
                      >
                        ✓ Required history
                        complete
                      </p>
                    ) : (
                      <>
                        <p
                          className="text-sm font-semibold"
                          style={{
                            color:
                              theme.charcoal,
                          }}
                        >
                          {
                            requiredUploadedCount
                          }{" "}
                          of{" "}
                          {
                            requiredMonths.length
                          }{" "}
                          required months
                          uploaded
                        </p>

                        <p
                          className="mt-1 text-sm"
                          style={{
                            color:
                              theme.brown,
                          }}
                        >
                          Upload the missing
                          month
                          {requiredMonths.length -
                            requiredUploadedCount ===
                          1
                            ? ""
                            : "s"}{" "}
                          above to run your
                          analysis.
                        </p>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* -----------------------------
                  12 month status
              ----------------------------- */}

              {canPossiblyHave12Months &&
                hasAllRequiredMonths && (
                  <div
                    className="mt-8 border-t pt-6"
                    style={{
                      borderColor: theme.line,
                    }}
                  >
                    {has12MonthHistory ? (
                      <p
                        className="text-sm"
                        style={{
                          color: theme.brown,
                        }}
                      >
                        You&apos;ve uploaded 12
                        consecutive months, so
                        SKUba can include its
                        deeper historical
                        analyses.
                      </p>
                    ) : (
                      <p
                        className="text-sm"
                        style={{
                          color: theme.brown,
                        }}
                      >
                        Your analysis is ready.
                        Upload the full latest 12
                        months if you want SKUba
                        to include analyses that
                        require deeper historical
                        context.
                      </p>
                    )}
                  </div>
                )}

              <div
                className="my-8 border-t"
                style={{
                  borderColor: theme.line,
                }}
              />

              {/* -----------------------------
                  Upload
              ----------------------------- */}

              <p
                className="mb-5 text-sm leading-6"
                style={{
                  color: theme.brown,
                }}
              >
                Upload your KeHE CSV reports.
                You can upload months one at a
                time and your coverage will
                update automatically.
              </p>

              <KeheUploadCard
                apiBaseUrl={apiBaseUrl}
                onUploadSuccess={
                  refreshKeheCoverage
                }
              />
            </section>
          )}

          {/* -----------------------------
              UNFI placeholder
          ----------------------------- */}

          {unfi && (
            <section
              className="border p-6 md:p-8"
              style={{
                background: theme.surface,
                borderColor: theme.line,
              }}
            >
              <h2
                className="text-2xl font-semibold"
                style={{
                  color: theme.charcoal,
                }}
              >
                UNFI
              </h2>

              <p
                className="mt-3 max-w-xl text-sm leading-6"
                style={{
                  color: theme.brown,
                }}
              >
                Self-serve UNFI upload is coming
                next. For now, your free analysis
                can be generated from your KeHE
                data.
              </p>
            </section>
          )}

        </div>

        {/* -----------------------------
            Continue
        ----------------------------- */}

        {kehe && (
          <div className="mt-8 flex flex-col items-end gap-2">
            <button
              type="button"
              disabled={!hasAllRequiredMonths}
              onClick={() =>
                router.push("/free-trial")
              }
              className="px-6 py-3 text-sm font-semibold transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
              style={{
                background: theme.charcoal,
                color: theme.surface,
              }}
            >
              Run my analysis
            </button>

            {!hasAllRequiredMonths && (
              <p
                className="text-xs"
                style={{
                  color: theme.muted,
                }}
              >
                Complete the required months
                above to continue.
              </p>
            )}

            {analysisTier && (
              <p
                className="text-xs"
                style={{
                  color: theme.muted,
                }}
              >
                Analysis history:{" "}
                {analysisTier === "12m"
                  ? "12+ months"
                  : analysisTier === "6m"
                    ? "6 months"
                    : "complete history"}
              </p>
            )}
          </div>
        )}

      </div>
    </main>
  )
}