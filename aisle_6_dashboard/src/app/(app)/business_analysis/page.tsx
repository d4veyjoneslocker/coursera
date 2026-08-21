"use client"

import { useEffect, useMemo, useRef, useState } from "react"

import { useOrg } from "@/components/OrgContext"
import FilterBar from "@/components/ui/filters/FilterBar"

import BusinessAnalysisView from "@/components/Business_Analysis"
import BusinessSignals from "@/components/Business_Signals"
import BusinessStories from "@/components/Business_Stories"


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL


const DEFAULT_THEME = {
  primary_color: "#9A93B0",
  secondary_color: "#C58E82",
  accent_color: "#C8795A",
  charcoal: "#343332",
  cream: "#E9E2C8",
  bg: "#F6F2EA",
  line: "#E5DDD0",
  chip: "#EEF4F8",
  surface: "#FFFDF9",
}


const FILTER_KEYS = [
  "chain",
  "sku",
  "channel",
  "distributor",
  "dc",
  "state",
] as const


// ---------------------------------------------------------
// API URL
// ---------------------------------------------------------

function buildApiUrl(
  filters: Record<string, string[]>,
  orgId: string
) {
  const params = new URLSearchParams()

  params.set("org_id", orgId)

  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => {
      params.append(key, value)
    })
  })

  return `${API_BASE_URL}/business-analysis/?${params.toString()}`
}


// ---------------------------------------------------------
// Filter URL
// ---------------------------------------------------------

function buildFilterUrl(
  columnName: string,
  filters: Record<string, string[]>,
  orgId: string
) {
  const params = new URLSearchParams()

  params.set("column_name", columnName)
  params.set("org_id", orgId)

  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => {
      params.append(key, value)
    })
  })

  return `${API_BASE_URL}/business-analysis/filters?${params.toString()}`
}


// ---------------------------------------------------------
// Page
// ---------------------------------------------------------

export default function BusinessAnalysisPage() {
  const { org } = useOrg()

  const theme = useMemo(() => {
    return {
      ...DEFAULT_THEME,
      primary_color:
        org?.primary_color || DEFAULT_THEME.primary_color,
      secondary_color:
        org?.secondary_color || DEFAULT_THEME.secondary_color,
      accent_color:
        org?.accent_color || DEFAULT_THEME.accent_color,
      bg:
        org?.background_color || DEFAULT_THEME.bg,
    }
  }, [org])


  // -------------------------------------------------------
  // Filters
  // -------------------------------------------------------

  const [filters, setFilters] = useState<
    Record<string, string[]>
  >({
    chain: [],
    sku: [],
    channel: [],
    distributor: [],
    dc: [],
    state: [],
  })


  const [filterOptions, setFilterOptions] = useState<
    Record<string, string[]>
  >({
    chain: [],
    sku: [],
    channel: [],
    distributor: [],
    dc: [],
    state: [],
  })


  const [visibleFilters, setVisibleFilters] =
    useState<string[]>([
      "chain",
      "sku",
      "state",
      "channel",
    ])


  // -------------------------------------------------------
  // Data
  // -------------------------------------------------------

  const [data, setData] = useState<any>(null)

  const [isLoading, setIsLoading] =
    useState(true)

  const [error, setError] =
    useState("")

  const latestRequestRef = useRef(0)


  // -------------------------------------------------------
  // Load analysis + filter options
  // -------------------------------------------------------

  async function loadData() {
    if (!org?.id) return

    const requestId =
      ++latestRequestRef.current

    setIsLoading(true)
    setError("")

    try {

      // -----------------------------------------------
      // Build filter requests
      // -----------------------------------------------

      const filterRequests =
        Object.fromEntries(
          FILTER_KEYS.map((key) => [
            key,
            buildFilterUrl(
              key,
              filters,
              org.id
            ),
          ])
        )


      // -----------------------------------------------
      // Main analysis request
      // -----------------------------------------------

      const analysisUrl =
        buildApiUrl(
          filters,
          org.id
        )


      // -----------------------------------------------
      // Fetch everything together
      // -----------------------------------------------

      const requestMap = {
        ...filterRequests,
        analysis: analysisUrl,
      }


      const responseEntries =
        await Promise.all(
          Object.entries(
            requestMap
          ).map(
            async ([key, url]) => {

              const response =
                await fetch(url)

              const json =
                await response.json()

              if (!response.ok) {
                throw new Error(
                  json.detail ||
                  `Failed to load ${key}.`
                )
              }

              return [
                key,
                json,
              ] as const
            }
          )
        )


      const results =
        Object.fromEntries(
          responseEntries
        )


      // -----------------------------------------------
      // Ignore stale requests
      // -----------------------------------------------

      if (
        requestId !==
        latestRequestRef.current
      ) {
        console.log(
          "IGNORED STALE BUSINESS ANALYSIS RESPONSE",
          { requestId }
        )

        return
      }


      // -----------------------------------------------
      // Filter options
      // -----------------------------------------------

      setFilterOptions({
        chain:
          Array.isArray(results.chain)
            ? results.chain
            : [],

        sku:
          Array.isArray(results.sku)
            ? results.sku
            : [],

        channel:
          Array.isArray(results.channel)
            ? results.channel
            : [],

        distributor:
          Array.isArray(results.distributor)
            ? results.distributor
            : [],

        dc:
          Array.isArray(results.dc)
            ? results.dc
            : [],

        state:
          Array.isArray(results.state)
            ? results.state
            : [],
      })


      // -----------------------------------------------
      // Analysis + signals
      // -----------------------------------------------

      setData(
        results.analysis
      )

    } catch (err) {

      console.error(
        "Failed to load business analysis:",
        err
      )

      const message =
        err instanceof Error
          ? err.message
          : "Failed to load business analysis."

      setError(message)

    } finally {

      if (
        requestId ===
        latestRequestRef.current
      ) {
        setIsLoading(false)
      }

    }
  }


  // -------------------------------------------------------
  // Reload when filters change
  // -------------------------------------------------------

  useEffect(() => {
    loadData()
  }, [filters, org?.id])


  // -------------------------------------------------------
  // Page
  // -------------------------------------------------------

  return (
    <main
      className="min-h-screen p-8"
      style={{
        backgroundColor: theme.bg,
      }}
    >
      <div className="mx-auto max-w-7xl space-y-8">

        {/* ---------------------------------------------
            Header
        --------------------------------------------- */}

        <div>
          <h1
            className="text-2xl font-semibold"
            style={{
              color: theme.charcoal,
            }}
          >
            Business Analysis
          </h1>

          <p className="mt-1 text-sm text-neutral-500">
            Full-business evidence and detected signals.
          </p>
        </div>


        {/* ---------------------------------------------
            Filters
        --------------------------------------------- */}

        <FilterBar
          filters={filters}
          setFilters={setFilters}
          filterOptions={filterOptions}

          availableFilters={[
            "chain",
            "sku",
            "channel",
            "distributor",
            "dc",
            "state",
          ]}

          visibleFilters={
            visibleFilters
          }

          setVisibleFilters={
            setVisibleFilters
          }

          filterLabels={{
            chain: "Retailer",
            sku: "SKU",
            channel: "Channel",
            distributor: "Distributor",
            dc: "DC",
            state: "State",
          }}

          theme={theme}
        />


        {/* ---------------------------------------------
            Error
        --------------------------------------------- */}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}


        {/* ---------------------------------------------
            Loading
        --------------------------------------------- */}

        {isLoading && (
          <div className="rounded-2xl border bg-white p-6">
            <p className="text-sm text-neutral-500">
              Loading business analysis...
            </p>
          </div>
        )}


        {/* ---------------------------------------------
            Results
        --------------------------------------------- */}

        {!isLoading && data && (
          <div className="space-y-10">

            <section>
            <div className="mb-4">
                <h2 className="text-xl font-semibold">
                Business Stories
                </h2>

                <p className="mt-1 text-sm text-neutral-500">
                The most important patterns and what is driving them.
                </p>
            </div>

            <BusinessStories
                stories={data.stories ?? []}
            />
            </section>

            {/* Signals */}

            <section>
              <div className="mb-4">
                <h2
                  className="text-xl font-semibold"
                  style={{
                    color: theme.charcoal,
                  }}
                >
                  Detected Signals
                </h2>

                <p className="mt-1 text-sm text-neutral-500">
                  Notable patterns detected across the selected business.
                </p>
              </div>

              <BusinessSignals
                signals={
                  data.signals ?? []
                }
              />
            </section>


            {/* Raw evidence */}

            <section>
              <div className="mb-4">
                <h2
                  className="text-xl font-semibold"
                  style={{
                    color: theme.charcoal,
                  }}
                >
                  Underlying Evidence
                </h2>

                <p className="mt-1 text-sm text-neutral-500">
                  Metrics supporting the detected signals.
                </p>
              </div>

              <BusinessAnalysisView
                data={
                  data.analysis ?? {}
                }
              />
            </section>

          </div>
        )}

      </div>
    </main>
  )
}