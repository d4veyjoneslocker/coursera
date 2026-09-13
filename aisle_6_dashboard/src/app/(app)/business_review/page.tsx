"use client"

import { useEffect, useState } from "react"
import BusinessReview, {
  type BusinessReviewData,
} from "@/components/business-review/BusinessReview"
import BusinessReviewHeader from "@/components/business-review/BusinessReviewHeader"
import { useOrg } from "@/components/OrgContext"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL

type ReviewPeriod = "H1" | "H2" | "FY"
type ReviewComparison = "PY" | "PP"

export default function BusinessReviewPage() {
  const { org } = useOrg()

  const [period, setPeriod] =
    useState<ReviewPeriod>("H1")

  const [year, setYear] =
    useState<number>(2026)

  const [comparison, setComparison] =
    useState<ReviewComparison>("PP")

  const [data, setData] =
    useState<BusinessReviewData | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  useEffect(() => {
    if (!org?.id || !API_BASE_URL) return

    const controller = new AbortController()

    async function loadBusinessReview() {
      setLoading(true)
      setError(null)

      try {
        const params = new URLSearchParams({
          org_id: org.id,
          period,
          year: String(year),
          comparison,
        })

        const response = await fetch(
          `${API_BASE_URL}/business-review?${params.toString()}`,
          {
            signal: controller.signal,
          }
        )

        if (!response.ok) {
          throw new Error(
            `Business review request failed: ${response.status}`
          )
        }

        const result: BusinessReviewData =
          await response.json()

        setData(result)
      } catch (err) {
        if (
          err instanceof DOMException &&
          err.name === "AbortError"
        ) {
          return
        }

        console.error(
          "Failed to load business review:",
          err
        )

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load business review."
        )
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadBusinessReview()

    return () => {
      controller.abort()
    }
  }, [
    org?.id,
    period,
    year,
    comparison,
  ])

  if (!org) {
    return null
  }

  /*
   * INITIAL LOAD + REFRESH LOAD
   *
   * Keep the real header visible so the page doesn't disappear
   * when switching period/year/comparison.
   */
  if (loading) {
    return (
      <div className="min-h-screen bg-[#FBFAF8] text-neutral-950">
        <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-12 lg:py-12">
          <BusinessReviewHeader
            period={period}
            year={year}
            comparison={comparison}
            years={[2025, 2026]}
            headline={
              data?.hero.headline ??
              "Building your business review."
            }
            summary={
              data?.hero.summary ??
              "SKUba is analyzing performance across your distributor data."
            }
            comparisonLabel={
              data?.meta.comparison.label ??
              getFallbackComparisonLabel(
                period,
                year,
                comparison
              )
            }
            onPeriodChange={setPeriod}
            onYearChange={setYear}
            onComparisonChange={setComparison}
          />

          <BusinessReviewSkeleton />
        </main>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-[#FBFAF8] text-neutral-950">
        <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:px-12 lg:py-12">
          <BusinessReviewHeader
            period={period}
            year={year}
            comparison={comparison}
            years={[2025, 2026]}
            headline="Business Review"
            summary="We couldn't load this review."
            comparisonLabel={getFallbackComparisonLabel(
              period,
              year,
              comparison
            )}
            onPeriodChange={setPeriod}
            onYearChange={setYear}
            onComparisonChange={setComparison}
          />

          <div className="mx-auto max-w-5xl py-10">
            <div className="border-y border-red-200 bg-red-50/60 py-5">
              <div className="text-sm font-semibold text-red-900">
                Couldn&apos;t load Business Review
              </div>

              <div className="mt-1 text-sm text-red-700">
                {error}
              </div>
            </div>
          </div>
        </main>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <BusinessReview
      data={data}
      period={period}
      year={year}
      comparison={comparison}
      years={[2025, 2026]}
      onPeriodChange={setPeriod}
      onYearChange={setYear}
      onComparisonChange={setComparison}
    />
  )
}

function BusinessReviewSkeleton() {
  return (
    <div className="mx-auto max-w-5xl animate-pulse pb-24">
      {/* scorecard */}
      <section className="border-t border-neutral-200 py-10">
        <div className="mb-7 flex items-end justify-between">
          <div>
            <div className="h-3 w-20 rounded bg-neutral-200" />
            <div className="mt-3 h-7 w-52 rounded bg-neutral-200" />
          </div>

          <div className="hidden h-4 w-36 rounded bg-neutral-200 sm:block" />
        </div>

        <div className="grid grid-cols-2 border-y border-neutral-200 md:grid-cols-5">
          {Array.from({ length: 5 }).map(
            (_, index) => (
              <div
                key={index}
                className="min-h-[120px] border-neutral-200 px-5 py-6 md:border-r md:last:border-r-0"
              >
                <div className="h-3 w-20 rounded bg-neutral-200" />
                <div className="mt-4 h-8 w-24 rounded bg-neutral-200" />
                <div className="mt-3 h-3 w-16 rounded bg-neutral-200" />
              </div>
            )
          )}
        </div>
      </section>

      {/* stories */}
      <section className="border-b border-neutral-200 py-12">
        <div className="h-3 w-24 rounded bg-neutral-200" />
        <div className="mt-3 h-8 w-64 rounded bg-neutral-200" />

        <div className="mt-8 space-y-8">
          {Array.from({ length: 3 }).map(
            (_, index) => (
              <div
                key={index}
                className="grid gap-5 border-t border-neutral-200 pt-7 sm:grid-cols-[42px_1fr]"
              >
                <div className="h-6 w-6 rounded-full bg-neutral-200" />

                <div>
                  <div className="h-5 max-w-xl rounded bg-neutral-200" />
                  <div className="mt-3 h-4 max-w-2xl rounded bg-neutral-200" />
                  <div className="mt-2 h-4 max-w-lg rounded bg-neutral-200" />
                </div>
              </div>
            )
          )}
        </div>
      </section>

      {/* momentum */}
      <section className="py-12">
        <div className="h-3 w-24 rounded bg-neutral-200" />
        <div className="mt-3 h-8 w-56 rounded bg-neutral-200" />

        <div className="mt-8 h-[280px] w-full rounded-xl bg-neutral-100" />
      </section>
    </div>
  )
}

function getFallbackComparisonLabel(
  period: ReviewPeriod,
  year: number,
  comparison: ReviewComparison
) {
  if (comparison === "PY") {
    return `${period} ${year - 1}`
  }

  if (period === "H2") {
    return `H1 ${year}`
  }

  if (period === "H1") {
    return `H2 ${year - 1}`
  }

  return `FY ${year - 1}`
}