"use client"

import React, { useEffect, useMemo, useRef, useState } from "react"



function formatMonthYear(value: string) {
  const [year, month] = value.split("-")
  const date = new Date(Number(year), Number(month) - 1)

  return date.toLocaleString("en-US", {
    month: "short",   // or "long" if you want "March 2025"
    year: "numeric",
  })
}

type Filters = Record<string, string[]>


type FilterBarProps = {
  filters: Filters
  setFilters: React.Dispatch<React.SetStateAction<Filters>>
  filterOptions: Filters
  availableFilters: string[]
  visibleFilters: string[]
  setVisibleFilters: React.Dispatch<React.SetStateAction<string[]>>
  filterLabels?: Record<string, string>
  theme: any 
}



const DEFAULT_LABELS: Record<string, string> = {
  chain: "Retailer",
  channel: "Channel",
  sku: "SKU",
  distributor: "Distributor",
  dc: "DC",
  state: "State",
  year: "Year",
  month_year: "Month",
  status: "Status",
}

type DropdownStyle = {
  top: number
  left: number
  width: number
}

export default function FilterBar({
  filters,
  setFilters,
  filterOptions,
  availableFilters,
  visibleFilters,
  setVisibleFilters,
  filterLabels,
  theme
}: FilterBarProps) {
  const labels = { ...DEFAULT_LABELS, ...filterLabels }

  const [isCustomizeOpen, setIsCustomizeOpen] = useState(false)
  const [isAllFiltersOpen, setIsAllFiltersOpen] = useState(false)
  const [openFilter, setOpenFilter] = useState<string | null>(null)
  const [dropdownStyle, setDropdownStyle] = useState<DropdownStyle | null>(null)
  const [searchByFilter, setSearchByFilter] = useState<Partial<Record<string, string>>>({})

  const customizePanelRef = useRef<HTMLDivElement | null>(null)
  const allFiltersPanelRef = useRef<HTMLDivElement | null>(null)
  const singleDropdownRef = useRef<HTMLDivElement | null>(null)
  const filterButtonRefs = useRef<Partial<Record<string, HTMLButtonElement | null>>>({})

  function getAccent(filterKey: string) {
    if (filterKey === "channel") return theme.secondary_color
    if (filterKey === "sku") return theme.charcoal
    if (filterKey === "year" || filterKey === "month_year") return theme.accent_color
    if (filterKey === "chain") return theme.primary_color
    return theme.primary_color
  }

  const SLOT_ACCENTS = [theme.primary_color, theme.secondary_color, theme.accent_color, theme.charcoal, theme.primary_color]

  const ALL_FILTER_CARD_ACCENTS = [
    theme.primary_color,
    theme.secondary_color,
    theme.accent_color,
    theme.charcoal,
    theme.primary_color,
    theme.secondary_color,
    theme.accent_color,
    theme.charcoal,
  ]

  useEffect(() => {
    const validVisible = visibleFilters.filter((f) => availableFilters.includes(f))
    const deduped = Array.from(new Set(validVisible))
    const missing = availableFilters.filter((f) => !deduped.includes(f))
    const nextVisible = [...deduped, ...missing].slice(0, Math.min(5, availableFilters.length))

    if (
      nextVisible.length !== visibleFilters.length ||
      nextVisible.some((f, i) => visibleFilters[i] !== f)
    ) {
      setVisibleFilters(nextVisible)
    }
  }, [availableFilters, visibleFilters, setVisibleFilters])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node

      const customizeButton = document.getElementById("customize-filters-button")
      const allFiltersButton = document.getElementById("all-filters-button")

      const clickedCustomizePanel = customizePanelRef.current?.contains(target)
      const clickedAllFiltersPanel = allFiltersPanelRef.current?.contains(target)
      const clickedSingleDropdown = singleDropdownRef.current?.contains(target)

      const clickedCustomizeButton = customizeButton?.contains(target)
      const clickedAllFiltersButton = allFiltersButton?.contains(target)

      const clickedTopFilterButton = Object.values(filterButtonRefs.current).some(
        (btn) => btn?.contains(target)
      )

      if (!clickedCustomizePanel && !clickedCustomizeButton) {
        setIsCustomizeOpen(false)
      }

      if (!clickedAllFiltersPanel && !clickedAllFiltersButton) {
        setIsAllFiltersOpen(false)
      }

      if (!clickedSingleDropdown && !clickedTopFilterButton) {
        setOpenFilter(null)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  useEffect(() => {
    function repositionDropdown() {
      if (!openFilter) return

      const button = filterButtonRefs.current[openFilter]
      if (!button) return

      const rect = button.getBoundingClientRect()

      setDropdownStyle({
        top: rect.bottom + 10,
        left: rect.left,
        width: Math.max(rect.width + 120, 360),
      })
    }

    if (openFilter) {
      repositionDropdown()
      window.addEventListener("resize", repositionDropdown)
      window.addEventListener("scroll", repositionDropdown, true)
    }

    return () => {
      window.removeEventListener("resize", repositionDropdown)
      window.removeEventListener("scroll", repositionDropdown, true)
    }
  }, [openFilter])

  const topFilters = useMemo(() => {
    return visibleFilters.filter((f) => availableFilters.includes(f)).slice(0, 5)
  }, [visibleFilters, availableFilters])

  const hiddenActiveFilters = useMemo(() => {
    return availableFilters.filter(
      (key) => !topFilters.includes(key) && (filters[key]?.length ?? 0) > 0
    )
  }, [availableFilters, topFilters, filters])

  function getDisplayValue(filterKey: string) {
    const selected = filters[filterKey] ?? []
    const label = labels[filterKey]

    if (selected.length === 0) {
      if (filterKey === "chain") return "All Retailers"
      if (filterKey === "channel") return "All Channels"
      if (filterKey === "sku") return "All SKUs"
      if (filterKey === "year") return "All Years"
      if (filterKey === "month_year") return "All Months"
      if (filterKey === "status") return "All Statuses"
      return `All ${label}s`
    }

    if (selected.length <= 2) {
      return selected
        .map((value) =>
          filterKey === "month_year" ? formatMonthYear(value) : value
        )
        .join(", ")
    }

    return `${selected.length} selected`
  }

  
  function toggleFilterValue(filterKey: string, value: string) {
    setFilters((prev) => {
      const current = prev[filterKey] ?? []
      const exists = current.includes(value)

      if (filterKey === "month_year") {
        return {
          ...prev,
          [filterKey]: exists ? [] : [value],
        }
      }

      return {
        ...prev,
        [filterKey]: exists ? current.filter((v) => v !== value) : [...current, value],
      }
    })
  }

  function clearFilter(filterKey: string) {
    setFilters((prev) => ({
      ...prev,
      [filterKey]: [],
    }))
  }

  function clearAllFilters() {
  setFilters((prev) =>
    Object.fromEntries(
      Object.keys(prev).map((key) => [key, []])
    )
  )
  }

  function replaceVisibleFilter(index: number, nextFilter: string) {
    setVisibleFilters((prev) => {
      const current = [...prev]

      if (current.includes(nextFilter) && current[index] !== nextFilter) {
        return current
      }

      current[index] = nextFilter
      return current
    })
  }

  function setSearch(filterKey: string, value: string) {
    setSearchByFilter((prev) => ({
      ...prev,
      [filterKey]: value,
    }))
  }

  function getFilteredOptions(filterKey: string) {
    let raw = filterOptions[filterKey] ?? []


    const q = (searchByFilter[filterKey] ?? "").trim().toLowerCase()

    if (!q) return raw

    return raw.filter((option) =>
      option.toLowerCase().includes(q)
    )
  }

  function activeCount(filterKey: string) {
    return filters[filterKey]?.length ?? 0
  }

  function openSingleFilter(filterKey: string) {
    const button = filterButtonRefs.current[filterKey]
    if (!button) return

    if (openFilter === filterKey) {
      setOpenFilter(null)
      return
    }

    const rect = button.getBoundingClientRect()

    setDropdownStyle({
      top: rect.bottom + 10,
      left: rect.left,
      width: Math.max(rect.width + 120, 360),
    })

    setOpenFilter(filterKey)
    setIsAllFiltersOpen(false)
    setIsCustomizeOpen(false)
  }

  const panelShellStyle: React.CSSProperties = {
    background:
      "linear-gradient(180deg, rgba(255,253,249,1) 0%, rgba(252,250,246,1) 100%)",
    borderColor: theme.line,
    boxShadow: "0 22px 60px rgba(52,51,50,0.14)",
  }

  const innerCardStyle: React.CSSProperties = {
    backgroundColor: "#FFFEFB",
    borderColor: "#EEE6DA",
  }

  return (
    <>
      <div
        className="relative rounded-[28px] border px-6 py-6 shadow-[0_10px_30px_rgba(52,51,50,0.05)]"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.line,
        }}
      >
        <div className="space-y-3">
          <p
            className="text-xs uppercase tracking-[0.2em]"
            style={{ color: theme.accent_color }}
          >
            Viewing
          </p>

          <div className="flex items-center gap-x-8 text-[28px] font-medium tracking-tight overflow-x-auto whitespace-nowrap">
            {topFilters.map((filterKey, i) => {
              const accent = getAccent(filterKey)

              return (
                <div key={filterKey} className="flex items-center gap-3">
                  <button
                    type="button"
                    ref={(el) => {
                      filterButtonRefs.current[filterKey] = el
                    }}
                    onClick={() => openSingleFilter(filterKey)}
                    className="relative inline-block min-w-[180px] pr-8 pb-1 text-left align-top transition hover:opacity-80"
                    style={{ color: theme.charcoal }}
                    title={`Edit ${labels[filterKey]}`}
                  >
                    {getDisplayValue(filterKey)}
                    <span
                      className="absolute inset-x-0 bottom-0 h-[2px] rounded-full opacity-80"
                      style={{ backgroundColor: accent }}
                    />
                  </button>

                  {i < topFilters.length - 1 && (
                    <span className="text-xl" style={{ color: "#B8AB97" }}>
                      •
                    </span>
                  )}
                </div>
              )
            })}
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            <button
              id="customize-filters-button"
              className="rounded-full border px-3 py-1.5 text-xs font-medium"
              style={{
                borderColor: "#D8CFBF",
                color: theme.accent_color,
                backgroundColor: "#FAF7F1",
              }}
              onClick={() => {
                setIsCustomizeOpen((prev) => !prev)
                setIsAllFiltersOpen(false)
                setOpenFilter(null)
              }}
            >
              Change shown filters
            </button>

            <button
              id="all-filters-button"
              className="rounded-full border px-3 py-1.5 text-xs font-medium"
              style={{
                borderColor: "#D8CFBF",
                color: theme.accent_color,
                backgroundColor: "#FAF7F1",
              }}
              onClick={() => {
                setIsAllFiltersOpen((prev) => !prev)
                setIsCustomizeOpen(false)
                setOpenFilter(null)
              }}
            >
              Filter data
            </button>

            <button
              className="rounded-full px-3 py-1.5 text-xs font-medium"
              style={{ color: theme.accent_color }}
              onClick={clearAllFilters}
            >
              Reset view
            </button>
          </div>

          {hiddenActiveFilters.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <div
                className="rounded-full border px-3 py-1 text-[11px] font-medium"
                style={{
                  borderColor: "#D8CFBF",
                  backgroundColor: "#FAF7F1",
                  color: theme.accent_color,
                }}
              >
                + {hiddenActiveFilters.length} more filter{hiddenActiveFilters.length > 1 ? "s" : ""} applied
              </div>

              {hiddenActiveFilters.map((key) => (
                <div
                  key={key}
                  className="rounded-full px-3 py-1 text-[11px] font-medium"
                  style={{
                    backgroundColor: theme.chip,
                    color: theme.charcoal,
                  }}
                >
                  {labels[key]}: {activeCount(key)}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {openFilter && dropdownStyle && (
        <div
          ref={singleDropdownRef}
          className="fixed z-50 max-h-[70vh] overflow-y-auto rounded-[28px] border p-5 animate-in fade-in zoom-in-95 duration-150"
          style={{
            top: dropdownStyle.top,
            left: dropdownStyle.left,
            width: dropdownStyle.width,
            ...panelShellStyle,
          }}
        >
          <div className="mb-4 flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div
                className="h-10 w-[4px] rounded-full"
                style={{ backgroundColor: getAccent(openFilter) }}
              />
              <div>
                <p
                  className="text-xs uppercase tracking-[0.18em]"
                  style={{ color: theme.accent_color }}
                >
                  Change {labels[openFilter].toLowerCase()}
                </p>
                <h2
                  className="mt-1 text-xl font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  {labels[openFilter]} selector
                </h2>
              </div>
            </div>

            <button
              className="rounded-full px-2.5 py-1 text-xs font-medium"
              style={{
                backgroundColor: theme.chip,
                color: theme.charcoal,
              }}
              onClick={() => setOpenFilter(null)}
            >
              close
            </button>
          </div>

          <div
            className="rounded-[22px] border p-4"
            style={innerCardStyle}
          >
            <input
              value={searchByFilter[openFilter] ?? ""}
              onChange={(e) => setSearch(openFilter, e.target.value)}
              placeholder={`Search ${labels[openFilter].toLowerCase()}...`}
              className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none"
              style={{
                borderColor: "#DDD4C6",
                backgroundColor: "#FFFDF9",
                color: theme.charcoal,
              }}
            />

            <div className="mt-4 max-h-[320px] space-y-2 overflow-y-auto pr-1">
              {getFilteredOptions(openFilter).map((item) => {
                const isSelected = (filters[openFilter] ?? []).includes(item)
                const accent = getAccent(openFilter)

                return (
                  <button
                    key={item}
                    className="flex w-full items-center justify-between rounded-2xl border px-3 py-3 text-left text-sm transition"
                    style={{
                      borderColor: isSelected ? "#CFE0EE" : "#EEE6DA",
                      backgroundColor: isSelected ? theme.chip : "#FFFEFB",
                      color: theme.charcoal,
                    }}
                    onClick={() => toggleFilterValue(openFilter, item)}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div
                        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold"
                        style={{
                          borderColor: isSelected ? accent : "#CFC3B1",
                          backgroundColor: isSelected ? accent : "transparent",
                          color: isSelected ? "white" : "transparent",
                        }}
                      >
                        ✓
                      </div>

                      <span className="truncate">
                        {openFilter === "month_year" ? formatMonthYear(item) : item}
                      </span>
                    </div>

                    {isSelected && (
                      <span
                        className="ml-3 shrink-0 text-xs font-medium"
                        style={{ color: theme.accent_color }}
                      >
                        selected
                      </span>
                    )}
                  </button>
                )
              })}

              {getFilteredOptions(openFilter).length === 0 && (
                <div
                  className="rounded-2xl border px-3 py-6 text-center text-sm"
                  style={innerCardStyle}
                >
                  No options found
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 flex gap-3">
            <button
              className="text-sm font-medium"
              style={{ color: getAccent(openFilter) }}
              onClick={() => clearFilter(openFilter)}
            >
              Clear
            </button>

            <button
              className="text-sm font-medium"
              style={{ color: theme.accent_color }}
              onClick={() => setOpenFilter(null)}
            >
              Done
            </button>
          </div>
        </div>
      )}

      {isCustomizeOpen && (
        <div className="fixed inset-0 z-40 bg-black/10">
          <div
            ref={customizePanelRef}
            className="absolute left-1/2 top-1/2 max-h-[85vh] w-[min(1100px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-[28px] border p-6"
            style={panelShellStyle}
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div
                  className="h-10 w-[4px] rounded-full"
                  style={{ backgroundColor: theme.primary_color }}
                />
                <div>
                  <p
                    className="text-xs uppercase tracking-[0.18em]"
                    style={{ color: theme.accent_color }}
                  >
                    Customize
                  </p>
                  <h2
                    className="mt-1 text-xl font-semibold"
                    style={{ color: theme.charcoal }}
                  >
                    Visible filters
                  </h2>
                </div>
              </div>

              <button
                className="rounded-full px-2.5 py-1 text-xs font-medium"
                style={{
                  backgroundColor: theme.chip,
                  color: theme.charcoal,
                }}
                onClick={() => setIsCustomizeOpen(false)}
              >
                close
              </button>
            </div>

            <p className="mb-6 text-sm" style={{ color: "#7A746B" }}>
              Choose which 5 filters appear in the viewing bar.
            </p>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {topFilters.map((currentFilter, index) => {
            const slotAccent = SLOT_ACCENTS[index] ?? theme.primary_color

            return (
                <div
                key={`${currentFilter}-${index}`}
                className="rounded-[24px] border p-4"
                style={innerCardStyle}
                >
                  <div className="mb-3 flex items-center gap-3">
                    <div
                      className="h-[3px] w-10 rounded-full"
                      style={{ backgroundColor: slotAccent }}
                    />
                    <p
                      className="text-xs uppercase tracking-[0.16em]"
                      style={{ color: theme.accent_color }}
                    >
                      Filter {index + 1}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    {availableFilters.map((candidate) => {
                      const active = visibleFilters[index] === candidate
                      const alreadyUsedElsewhere =
                        visibleFilters.includes(candidate) && visibleFilters[index] !== candidate

                      return (
                        <button
                          key={`${index}-${candidate}`}
                          onClick={() => replaceVisibleFilter(index, candidate)}
                          disabled={alreadyUsedElsewhere}
                          className="rounded-2xl border px-3 py-3 text-left text-sm transition"
                          style={{
                            borderColor: active ? `${slotAccent}55` : "#EEE6DA",
                            backgroundColor: active ? `${slotAccent}22` : "#FFFEFB",
                            color: alreadyUsedElsewhere ? "#B8AB97" : theme.charcoal,
                            opacity: alreadyUsedElsewhere ? 0.6 : 1,
                          }}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span>{labels[candidate]}</span>
                            {active && (
                              <span
                                className="text-xs font-medium"
                                style={{ color: theme.accent_color }}
                              >
                                selected
                              </span>
                            )}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}
            </div>
          </div>
        </div>
      )}

      {isAllFiltersOpen && (
        <div className="fixed inset-0 z-40 bg-black/10">
          <div
            ref={allFiltersPanelRef}
            className="absolute left-1/2 top-1/2 max-h-[85vh] w-[min(1200px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-[28px] border p-6"
            style={panelShellStyle}
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div
                  className="h-10 w-[4px] rounded-full"
                  style={{ backgroundColor: theme.primary_color }}
                />
                <div>
                  <p
                    className="text-xs uppercase tracking-[0.18em]"
                    style={{ color: theme.accent_color }}
                  >
                    Filter data
                  </p>
                  <h2
                    className="mt-1 text-xl font-semibold"
                    style={{ color: theme.charcoal }}
                  >
                    All filters
                  </h2>
                </div>
              </div>

              <button
                className="rounded-full px-2.5 py-1 text-xs font-medium"
                style={{
                  backgroundColor: theme.chip,
                  color: theme.charcoal,
                }}
                onClick={() => setIsAllFiltersOpen(false)}
              >
                close
              </button>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {availableFilters.map((filterKey, index) => {
                const cardAccent = ALL_FILTER_CARD_ACCENTS[index] ?? theme.primary_color

                return (
                <div
                  key={filterKey}
                  className="rounded-[24px] border p-4"
                  style={innerCardStyle}
                >
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div
                        className="h-[3px] w-10 rounded-full shrink-0"
                        style={{ backgroundColor: cardAccent }}
                        />
                    <div>
                      <p
                        className="text-xs uppercase tracking-[0.16em]"
                        style={{ color: theme.accent_color }}
                      >
                        {labels[filterKey]}
                      </p>
                      <p
                        className="mt-1 text-sm"
                        style={{ color: "#7A746B" }}
                      >
                        {activeCount(filterKey) > 0
                          ? `${activeCount(filterKey)} selected`
                          : "No filter applied"}
                      </p>
                    </div>

                    <button
                      className="text-sm font-medium"
                      style={{ color: getAccent(filterKey) }}
                      onClick={() => clearFilter(filterKey)}
                    >
                      Clear
                    </button>
                  </div>

                  <div
                    className="rounded-[20px] border p-3"
                    style={{
                      backgroundColor: "#FFFDF9",
                      borderColor: "#EEE6DA",
                    }}
                  >
                    <input
                      value={searchByFilter[filterKey] ?? ""}
                      onChange={(e) => setSearch(filterKey, e.target.value)}
                      placeholder={`Search ${labels[filterKey].toLowerCase()}...`}
                      className="w-full rounded-xl border px-3 py-2.5 text-sm outline-none"
                      style={{
                        borderColor: "#DDD4C6",
                        backgroundColor: "#FFFEFB",
                        color: theme.charcoal,
                      }}
                    />

                    <div className="mt-3 max-h-[260px] space-y-2 overflow-y-auto pr-1">
                      {getFilteredOptions(filterKey).map((item) => {
                        const isSelected = (filters[filterKey] ?? []).includes(item)
                        const accent = getAccent(filterKey)

                        return (
                          <button
                            key={item}
                            className="flex w-full items-center justify-between rounded-2xl border px-3 py-3 text-left text-sm transition"
                            style={{
                              borderColor: isSelected ? "#CFE0EE" : "#EEE6DA",
                              backgroundColor: isSelected ? theme.chip : "#FFFEFB",
                              color: theme.charcoal,
                            }}
                            onClick={() => toggleFilterValue(filterKey, item)}
                          >
                            <div className="flex min-w-0 items-center gap-3">
                              <div
                                className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold"
                                style={{
                                  borderColor: isSelected ? accent : "#CFC3B1",
                                  backgroundColor: isSelected ? accent : "transparent",
                                  color: isSelected ? "white" : "transparent",
                                }}
                              >
                                ✓
                              </div>

                              <span className="truncate">
                                {filterKey === "month_year" ? formatMonthYear(item) : item}
                              </span>
                            </div>

                            {isSelected && (
                              <span
                                className="ml-3 shrink-0 text-xs font-medium"
                                style={{ color: theme.accent_color }}
                              >
                                selected
                              </span>
                            )}
                          </button>
                        )
                      })}

                      {getFilteredOptions(filterKey).length === 0 && (
                        <div
                          className="rounded-2xl border px-3 py-6 text-center text-sm"
                          style={innerCardStyle}
                        >
                          No options found
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
            </div>

            <div className="mt-5 flex gap-3">
              <button
                className="text-sm font-medium"
                style={{ color: theme.accent_color }}
                onClick={() => setIsAllFiltersOpen(false)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}