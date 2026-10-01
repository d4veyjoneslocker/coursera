"use client"

import { useEffect, useMemo, useRef, useState } from "react"

import { useOrg } from "@/components/OrgContext"
import StoreHealthMap from "@/components/StoreHealthMap"
import DashboardHeader from "@/components/ui/DashboardHeader"
import FilterBar from "@/components/ui/filters/FilterBar"


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


const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL


const DATA_ENDPOINTS = {
  status: "store_health/status",
  storeTable: "store_health/store_performance",
  filters: "store_health/filters",
} as const


const STATUS_STYLES: Record<
  string,
  {
    bg: string
    text: string
    border: string
  }
> = {
  Healthy: {
    bg: "#F0F6F2",
    text: "#65A57B",
    border: "#D8E8DD",
  },
  Struggling: {
    bg: "#F9F0F0",
    text: "#C97474",
    border: "#ECD8D8",
  },
  Revived: {
    bg: "#FAF3EB",
    text: "#D39A5B",
    border: "#EDDDCA",
  },
  New: {
    bg: "#F3F1F6",
    text: "#9A93B0",
    border: "#DFDCE7",
  },
  Inactive: {
    bg: "#F3F3F2",
    text: "#999A9D",
    border: "#E2E2E0",
  },
}


const STATUS_ORDER = [
  "Healthy",
  "Struggling",
  "Revived",
  "New",
  "Inactive",
]


type StatusCounts = Record<string, number>


type StoreRow = {
  coded_customer: string | null
  chain: string | null

  units: number | null
  revenue: number | null
  reorders: number | null
  vpo: number | null
  skus_selling: number | null

  distributor: string | null
  dc: string | null

  first_month_purchased: string | null
  last_month_purchased: string | null
  status: string | null

  latitude: number | null
  longitude: number | null
}


function buildApiUrl(
  endpoint: string,
  filters: Record<string, string[]>,
  orgId: string
) {
  const params = new URLSearchParams()

  params.set("org_id", orgId)

  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => params.append(key, value))
  })

  return `${API_BASE_URL}/${endpoint}?${params.toString()}`
}


function buildFilterUrl(
  columnName: string,
  filters: Record<string, string[]>,
  orgId: string
) {
  const params = new URLSearchParams()

  params.set("column_name", columnName)
  params.set("org_id", orgId)

  Object.entries(filters).forEach(([key, values]) => {
    values.forEach((value) => params.append(key, value))
  })

  return `${API_BASE_URL}/${DATA_ENDPOINTS.filters}?${params.toString()}`
}


function StatusPill({
  status,
}: {
  status: string
}) {
  const style =
    STATUS_STYLES[status] ??
    STATUS_STYLES.Inactive

  return (
    <span
      className="inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium"
      style={{
        backgroundColor: style.bg,
        color: style.text,
        borderColor: style.border,
      }}
    >
      {status}
    </span>
  )
}


function StatusCountPill({
  status,
  count,
  active,
  onClick,
  isLast,
}: {
  status: string
  count: number
  active: boolean
  onClick: () => void
  isLast: boolean
}) {
  const style =
    STATUS_STYLES[status] ??
    STATUS_STYLES.Inactive

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-w-0 items-center justify-between gap-4 px-6 py-5 text-left transition-colors hover:bg-black/[0.02]"
      style={{
        backgroundColor: active
          ? style.bg
          : "transparent",
        borderRight: isLast
          ? "none"
          : "1px solid #E5DDD0",
      }}
    >
      <div className="flex min-w-0 items-center gap-2.5">
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-full"
          style={{
            backgroundColor: style.text,
          }}
        />

        <span
          className="truncate text-sm font-medium"
          style={{
            color: active
              ? style.text
              : "#6B6B6B",
          }}
        >
          {status}
        </span>
      </div>

      <span
        className="shrink-0 text-xl font-semibold"
        style={{
          color: active
            ? style.text
            : "#343332",
        }}
      >
        {count.toLocaleString()}
      </span>
    </button>
  )
}


function SortableHeader({
  label,
  column,
  sortKey,
  sortDirection,
  onSort,
}: {
  label: string
  column: string
  sortKey: string | null
  sortDirection: "asc" | "desc"
  onSort: (key: string) => void
}) {
  const isActive = sortKey === column

  return (
    <th
      onClick={() => onSort(column)}
      className="group cursor-pointer px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-white"
    >
      <div className="flex items-center gap-1">
        <span>{label}</span>

        <span
          className={`text-[10px] transition-opacity ${
            isActive
              ? "opacity-100"
              : "opacity-0 group-hover:opacity-60"
          }`}
        >
          {isActive
            ? sortDirection === "asc"
              ? "↑"
              : "↓"
            : "↕"}
        </span>
      </div>
    </th>
  )
}


export default function StoresPage() {
  const { org } = useOrg()


  const theme = useMemo(() => {
    return {
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
      bg:
        org?.background_color ||
        DEFAULT_THEME.bg,
    }
  }, [org])


  const FILTER_KEYS = [
    "chain",
    "channel",
    "distributor",
    "dc",
    "state",
    "status",
  ] as const


  const [filters, setFilters] = useState<
    Record<string, string[]>
  >({
    chain: [],
    channel: [],
    distributor: [],
    dc: [],
    state: [],
    status: [],
  })


  const [filterOptions, setFilterOptions] =
    useState<Record<string, string[]>>({
      chain: [],
      channel: [],
      distributor: [],
      dc: [],
      state: [],
      status: [],
    })


  const [visibleFilters, setVisibleFilters] =
    useState<string[]>([
      "chain",
      "channel",
      "distributor",
      "status",
    ])


  const latestRequestRef = useRef(0)


  const [statusCounts, setStatusCounts] =
    useState<StatusCounts>({})


  const [storeTableData, setStoreTableData] =
    useState<StoreRow[]>([])


  const [sortKey, setSortKey] =
    useState<string | null>(null)


  const [sortDirection, setSortDirection] =
    useState<"asc" | "desc">("desc")


  const processedStoreTableData = useMemo(() => {
    return [...storeTableData].sort((a, b) => {
      if (!sortKey) return 0

      const aVal =
        a[sortKey as keyof StoreRow]

      const bVal =
        b[sortKey as keyof StoreRow]

      if (aVal == null) return 1
      if (bVal == null) return -1

      if (
        typeof aVal === "number" &&
        typeof bVal === "number"
      ) {
        return sortDirection === "asc"
          ? aVal - bVal
          : bVal - aVal
      }

      return sortDirection === "asc"
        ? String(aVal).localeCompare(
            String(bVal)
          )
        : String(bVal).localeCompare(
            String(aVal)
          )
    })
  }, [
    storeTableData,
    sortKey,
    sortDirection,
  ])


  function handleSort(key: string) {
    if (sortKey !== key) {
      setSortKey(key)
      setSortDirection("desc")
    } else if (sortDirection === "desc") {
      setSortDirection("asc")
    } else {
      setSortKey(null)
    }
  }


  async function loadData() {
    if (!org?.id) return

    const requestId =
      ++latestRequestRef.current

    try {
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


      const dataRequests = {
        status: buildApiUrl(
          DATA_ENDPOINTS.status,
          filters,
          org.id
        ),

        storeTable: buildApiUrl(
          DATA_ENDPOINTS.storeTable,
          filters,
          org.id
        ),
      }


      const requestMap = {
        ...filterRequests,
        ...dataRequests,
      }


      const responseEntries =
        await Promise.all(
          Object.entries(requestMap).map(
            async ([key, url]) => {
              const response =
                await fetch(url)

              if (!response.ok) {
                throw new Error(
                  `${key} request failed with ${response.status}`
                )
              }

              const json =
                await response.json()

              return [key, json] as const
            }
          )
        )


      const results =
        Object.fromEntries(
          responseEntries
        )


      if (
        requestId !==
        latestRequestRef.current
      ) {
        console.log(
          "IGNORED STALE STORE HEALTH RESPONSE",
          { requestId }
        )

        return
      }


      setFilterOptions({
        chain: Array.isArray(results.chain)
          ? results.chain
          : [],

        channel: Array.isArray(
          results.channel
        )
          ? results.channel
          : [],

        distributor: Array.isArray(
          results.distributor
        )
          ? results.distributor
          : [],

        dc: Array.isArray(results.dc)
          ? results.dc
          : [],

        state: Array.isArray(results.state)
          ? results.state
          : [],

        status: Array.isArray(
          results.status
        )
          ? results.status
          : [],
      })


      setStatusCounts(
        results.status &&
          !Array.isArray(results.status)
          ? results.status
          : {}
      )


      setStoreTableData(
        Array.isArray(results.storeTable)
          ? results.storeTable
          : []
      )
    } catch (error) {
      console.error(
        "Failed to load store health page data:",
        error
      )
    }
  }


  useEffect(() => {
    loadData()
  }, [filters, org?.id])


  const [dataThrough, setDataThrough] =
    useState<string | undefined>()


  const [isStale, setIsStale] =
    useState(false)


  const formatMonthYear = (
    value?: string
  ) => {
    if (!value) return undefined

    const [year, month] =
      value.split("-")

    const date = new Date(
      Number(year),
      Number(month) - 1
    )

    return date.toLocaleString(
      "en-US",
      {
        month: "long",
        year: "numeric",
      }
    )
  }


  const fetchStatus = async () => {
    if (!org?.id) return

    try {
      const res = await fetch(
        `${API_BASE_URL}/distributors/kehe/status?org_id=${org.id}`
      )

      const data = await res.json()

      if (data.status === "ready") {
        setDataThrough(
          formatMonthYear(
            data.data_through
          )
        )

        setIsStale(data.is_stale)
      }
    } catch (err) {
      console.error(
        "Failed to fetch status",
        err
      )
    }
  }


  useEffect(() => {
    fetchStatus()
  }, [org?.id])


  function handleStatusClick(
    status: string
  ) {
    setFilters((prev) => {
      const selectedStatuses =
        prev.status ?? []

      const alreadySelected =
        selectedStatuses.length === 1 &&
        selectedStatuses[0] === status

      return {
        ...prev,
        status: alreadySelected
          ? []
          : [status],
      }
    })
  }


  return (
    <main
      className="min-h-screen"
      style={{
        backgroundColor: theme.bg,
      }}
    >
      <DashboardHeader
        activePage="stores"
        dataThrough={dataThrough}
        isStale={isStale}
        onDataRefresh={async () => {
          await fetchStatus()
          await loadData()
        }}
      />


      <div className="ml-[238px] min-h-screen p-8">
        <div className="mx-auto max-w-7xl space-y-8">


          <FilterBar
            filters={filters}
            setFilters={setFilters}
            filterOptions={filterOptions}
            availableFilters={[
              "chain",
              "channel",
              "distributor",
              "dc",
              "state",
              "status",
            ]}
            visibleFilters={
              visibleFilters
            }
            setVisibleFilters={
              setVisibleFilters
            }
            filterLabels={{
              chain: "Retailer",
              channel: "Channel",
              distributor:
                "Distributor",
              dc: "DC",
              state: "State",
              status: "Status",
            }}
            theme={theme}
          />


          <div
            className="rounded-[28px] border p-6 shadow-sm"
            style={{
              backgroundColor:
                theme.surface,
              borderColor: theme.line,
            }}
          >
            <div className="mb-5 flex items-center gap-3">
              <div
                className="h-[3px] w-24 rounded-full"
                style={{
                  backgroundColor:
                    theme.charcoal +
                    "CC",
                }}
              />

              <p
                className="text-[16px] font-medium uppercase tracking-[0.18em]"
                style={{
                  color: "#6B6B6B",
                }}
              >
                STORE HEALTH MAP
              </p>
            </div>


              <StoreHealthMap
                stores={storeTableData}
              />
          </div>


          <div
            className="overflow-hidden rounded-[28px] border shadow-sm"
            style={{
              backgroundColor:
                theme.surface,
              borderColor: theme.line,
            }}
          >
            <div className="p-6 pb-5">
              <div className="flex items-center gap-3">
                <div
                  className="h-[3px] w-24 rounded-full"
                  style={{
                    backgroundColor:
                      theme.secondary_color +
                      "CC",
                  }}
                />

                <p
                  className="text-[16px] font-medium uppercase tracking-[0.18em]"
                  style={{
                    color: "#6B6B6B",
                  }}
                >
                  STORE STATUS
                </p>
              </div>
            </div>


            <div
              className="grid w-full grid-cols-5 border-t"
              style={{
                borderColor: theme.line,
              }}
            >
              {STATUS_ORDER.map(
                (status, index) => {
                  const selectedStatuses =
                    filters.status ?? []

                  const active =
                    selectedStatuses.includes(
                      status
                    )

                  return (
                    <StatusCountPill
                      key={status}
                      status={status}
                      count={Number(
                        statusCounts[
                          status
                        ] ?? 0
                      )}
                      active={active}
                      isLast={
                        index ===
                        STATUS_ORDER.length - 1
                      }
                      onClick={() =>
                        handleStatusClick(
                          status
                        )
                      }
                    />
                  )
                }
              )}
            </div>
          </div>


          <div
            className="rounded-[28px] border p-6 shadow-sm"
            style={{
              backgroundColor:
                theme.surface,
              borderColor: theme.line,
            }}
          >
            <div className="mb-5 flex items-center gap-3">
              <div
                className="h-[3px] w-24 rounded-full"
                style={{
                  backgroundColor:
                    theme.accent_color +
                    "CC",
                }}
              />

              <p
                className="text-[16px] font-medium uppercase tracking-[0.18em]"
                style={{
                  color: "#6B6B6B",
                }}
              >
                STORE PERFORMANCE
              </p>
            </div>


            <div className="overflow-hidden rounded-[20px] border border-black/10">
              <div className="max-h-[520px] overflow-auto">
                <table className="w-full text-sm">
                  <thead
                    className="sticky top-0 z-10"
                    style={{
                      backgroundColor:
                        theme.primary_color,
                    }}
                  >
                    <tr className="[&_th]:px-4 [&_th]:py-3 [&_th]:text-left [&_th]:text-[11px] [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-[0.14em] [&_th]:text-white">
                      <SortableHeader
                        label="Store"
                        column="coded_customer"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="Retailer"
                        column="chain"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="Units"
                        column="units"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="Revenue"
                        column="revenue"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="Reorders"
                        column="reorders"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="VPO"
                        column="vpo"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="SKUs Selling"
                        column="skus_selling"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="Distributor"
                        column="distributor"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="DC"
                        column="dc"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="First Month"
                        column="first_month_purchased"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="Last Month"
                        column="last_month_purchased"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />

                      <SortableHeader
                        label="Status"
                        column="status"
                        sortKey={sortKey}
                        sortDirection={
                          sortDirection
                        }
                        onSort={
                          handleSort
                        }
                      />
                    </tr>
                  </thead>


                  <tbody>
                    {processedStoreTableData.length >
                    0 ? (
                      processedStoreTableData.map(
                        (row, index) => (
                          <tr
                            key={`${row.coded_customer}-${index}`}
                            className="border-b border-black/5"
                          >
                            <td className="px-4 py-3 font-medium text-neutral-900">
                              {row.coded_customer ??
                                "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.chain ??
                                "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.units !=
                              null
                                ? Number(
                                    row.units
                                  ).toLocaleString()
                                : "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.revenue !=
                              null
                                ? `$${Number(
                                    row.revenue
                                  ).toLocaleString(
                                    undefined,
                                    {
                                      maximumFractionDigits: 0,
                                    }
                                  )}`
                                : "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.reorders !=
                              null
                                ? Number(
                                    row.reorders
                                  ).toLocaleString()
                                : "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.vpo !=
                              null
                                ? Number(
                                    row.vpo
                                  ).toFixed(
                                    1
                                  )
                                : "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.skus_selling !=
                              null
                                ? Number(
                                    row.skus_selling
                                  ).toLocaleString()
                                : "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.distributor ??
                                "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.dc ??
                                "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.first_month_purchased ??
                                "—"}
                            </td>

                            <td className="px-4 py-3 text-neutral-700">
                              {row.last_month_purchased ??
                                "—"}
                            </td>

                            <td className="px-4 py-3">
                              <StatusPill
                                status={
                                  row.status ??
                                  "Inactive"
                                }
                              />
                            </td>
                          </tr>
                        )
                      )
                    ) : (
                      <tr>
                        <td
                          colSpan={12}
                          className="px-4 py-10 text-center text-sm text-neutral-500"
                        >
                          No stores match
                          the selected
                          filters.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>


        </div>
      </div>
    </main>
  )
}