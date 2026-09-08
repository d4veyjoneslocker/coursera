"use client"

import { useState } from "react"

// =========================================================
// Types
// =========================================================

export type ProductSource = "kehe" | "unfi"

export type ReconciliationProduct = {
  id: string
  source: ProductSource
  rawSku: string
  rawUpc?: string | null
}

export type ReconciliationGroup = {
  id: string
  cleanSku: string
  unitsPerCase: number | ""
  products: ReconciliationProduct[]
}

type SKUReconciliationProps = {
  initialGroups: ReconciliationGroup[]
  initialUnassigned?: ReconciliationProduct[]
  onConfirm?: (groups: ReconciliationGroup[]) => void
  isSubmitting?: boolean
}

type ReconciliationPhase =
  | "matching"
  | "details"

// =========================================================
// Initial-state helpers
// =========================================================

function getInitialSources(
  initialGroups: ReconciliationGroup[],
  initialUnassigned: ReconciliationProduct[]
) {
  const sources = new Set<ProductSource>()

  initialGroups.forEach((group) => {
    group.products.forEach((product) => {
      sources.add(product.source)
    })
  })

  initialUnassigned.forEach((product) => {
    sources.add(product.source)
  })

  return sources
}

function buildInitialState(
  initialGroups: ReconciliationGroup[],
  initialUnassigned: ReconciliationProduct[]
) {
  const sources = getInitialSources(
    initialGroups,
    initialUnassigned
  )

  const hasMultipleDistributors =
    sources.has("kehe") &&
    sources.has("unfi")

  // -------------------------------------------------------
  // One distributor:
  //
  // There is nothing to match across distributors, so each
  // unmatched raw SKU becomes its own canonical product row.
  // -------------------------------------------------------

  if (!hasMultipleDistributors) {
    const existingProductIds = new Set(
      initialGroups.flatMap((group) =>
        group.products.map(
          (product) => product.id
        )
      )
    )

    const groupsFromUnassigned =
      initialUnassigned
        .filter(
          (product) =>
            !existingProductIds.has(product.id)
        )
        .map((product) => ({
          id: `single-${product.id}`,
          cleanSku: "",
          unitsPerCase: "" as const,
          products: [product],
        }))

    return {
      groups: [
        ...initialGroups,
        ...groupsFromUnassigned,
      ],
      unassigned: [] as ReconciliationProduct[],
      phase: "details" as ReconciliationPhase,
      hasMultipleDistributors,
      hasKehe: sources.has("kehe"),
      hasUnfi: sources.has("unfi"),
    }
  }

  // -------------------------------------------------------
  // Multiple distributors:
  //
  // Keep the existing suggested groups + unassigned pool
  // and start with product matching.
  // -------------------------------------------------------

  return {
    groups: initialGroups,
    unassigned: initialUnassigned,
    phase: "matching" as ReconciliationPhase,
    hasMultipleDistributors,
    hasKehe: true,
    hasUnfi: true,
  }
}

// =========================================================
// Component
// =========================================================

export default function SKUReconciliation({
  initialGroups,
  initialUnassigned = [],
  onConfirm,
  isSubmitting = false,
}: SKUReconciliationProps) {
  const [initialState] = useState(() =>
    buildInitialState(
      initialGroups,
      initialUnassigned
    )
  )

  const [groups, setGroups] =
    useState<ReconciliationGroup[]>(
      initialState.groups
    )

  const [unassigned, setUnassigned] =
    useState<ReconciliationProduct[]>(
      initialState.unassigned
    )

  const [phase, setPhase] =
    useState<ReconciliationPhase>(
      initialState.phase
    )

  const [selectedProduct, setSelectedProduct] =
    useState<ReconciliationProduct | null>(
      null
    )

  const [draggedProduct, setDraggedProduct] =
    useState<ReconciliationProduct | null>(
      null
    )

  const hasMultipleDistributors =
    initialState.hasMultipleDistributors

  const hasKehe =
    initialState.hasKehe

  const hasUnfi =
    initialState.hasUnfi

  const isMatchingPhase =
    phase === "matching"

  const isDetailsPhase =
    phase === "details"

  // =======================================================
  // Helpers
  // =======================================================

  const removeProductEverywhere = (
    productId: string,
    currentGroups: ReconciliationGroup[],
    currentUnassigned: ReconciliationProduct[]
  ) => {
    return {
      groups: currentGroups.map((group) => ({
        ...group,
        products: group.products.filter(
          (product) =>
            product.id !== productId
        ),
      })),

      unassigned:
        currentUnassigned.filter(
          (product) =>
            product.id !== productId
        ),
    }
  }

  const moveProductToGroup = (
    product: ReconciliationProduct,
    targetGroupId: string
  ) => {
    const cleaned = removeProductEverywhere(
      product.id,
      groups,
      unassigned
    )

    setGroups(
      cleaned.groups.map((group) =>
        group.id === targetGroupId
          ? {
              ...group,
              products: [
                ...group.products,
                product,
              ],
            }
          : group
      )
    )

    setUnassigned(
      cleaned.unassigned
    )

    setSelectedProduct(null)
    setDraggedProduct(null)
  }

  const moveProductToUnassigned = (
    product: ReconciliationProduct
  ) => {
    const cleaned = removeProductEverywhere(
      product.id,
      groups,
      unassigned
    )

    setGroups(cleaned.groups)

    setUnassigned([
      ...cleaned.unassigned,
      product,
    ])

    setSelectedProduct(null)
    setDraggedProduct(null)
  }

  // =======================================================
  // Group editing
  // =======================================================

  const updateCleanSku = (
    groupId: string,
    value: string
  ) => {
    setGroups((current) =>
      current.map((group) =>
        group.id === groupId
          ? {
              ...group,
              cleanSku: value,
            }
          : group
      )
    )
  }

  const updateUnitsPerCase = (
    groupId: string,
    value: string
  ) => {
    setGroups((current) =>
      current.map((group) =>
        group.id === groupId
          ? {
              ...group,
              unitsPerCase:
                value === ""
                  ? ""
                  : Number(value),
            }
          : group
      )
    )
  }

  // =======================================================
  // New canonical product
  // =======================================================

  const createGroup = () => {
    const newGroup: ReconciliationGroup = {
      id: `product-${Date.now()}`,
      cleanSku: "",
      unitsPerCase: "",
      products: [],
    }

    setGroups((current) => [
      ...current,
      newGroup,
    ])
  }

  // =======================================================
  // Drag handling
  // =======================================================

  const handleDragStart = (
    product: ReconciliationProduct
  ) => {
    if (!isMatchingPhase) return

    setDraggedProduct(product)
    setSelectedProduct(product)
  }

  const handleDropOnGroup = (
    groupId: string
  ) => {
    if (!isMatchingPhase) return
    if (!draggedProduct) return

    moveProductToGroup(
      draggedProduct,
      groupId
    )
  }

  const handleDropOnUnassigned = () => {
    if (!isMatchingPhase) return
    if (!draggedProduct) return

    moveProductToUnassigned(
      draggedProduct
    )
  }

  // =======================================================
  // Click-to-move
  // =======================================================

  const handleProductClick = (
    product: ReconciliationProduct
  ) => {
    if (!isMatchingPhase) return

    if (
      selectedProduct?.id === product.id
    ) {
      setSelectedProduct(null)
      return
    }

    setSelectedProduct(product)
  }

  const handleGroupClick = (
    groupId: string
  ) => {
    if (!isMatchingPhase) return
    if (!selectedProduct) return

    moveProductToGroup(
      selectedProduct,
      groupId
    )
  }

  // =======================================================
  // Validation
  // =======================================================

  const populatedGroups =
    groups.filter(
      (group) =>
        group.products.length > 0
    )

  const matchingComplete =
    unassigned.length === 0 &&
    populatedGroups.length > 0

  const detailsComplete =
    matchingComplete &&
    populatedGroups.every(
      (group) =>
        group.cleanSku.trim() !== "" &&
        group.unitsPerCase !== "" &&
        Number(group.unitsPerCase) > 0
    )

  const handleContinueToDetails = () => {
    if (!matchingComplete) return

    setSelectedProduct(null)
    setDraggedProduct(null)
    setPhase("details")
  }

  const handleBackToMatches = () => {
    setSelectedProduct(null)
    setDraggedProduct(null)
    setPhase("matching")
  }

  const handleConfirm = () => {
    if (!detailsComplete) return

    onConfirm?.(populatedGroups)
  }

  // =======================================================
  // Grid layouts
  // =======================================================

  const matchingGrid =
    "lg:grid-cols-[300px_28px_300px]"

  const multiDetailsGrid =
    "lg:grid-cols-[180px_260px_28px_260px_130px]"

  const singleKeheDetailsGrid =
    "lg:grid-cols-[220px_1fr_150px]"

  const singleUnfiDetailsGrid =
    "lg:grid-cols-[220px_1fr_150px]"

  const detailsGrid =
    hasMultipleDistributors
      ? multiDetailsGrid
      : hasKehe
        ? singleKeheDetailsGrid
        : singleUnfiDetailsGrid

  // =======================================================
  // Render
  // =======================================================

  return (
    <section className="w-full font-['Figtree']">
      {/* =================================================
          Header
      ================================================= */}

      <div className="mb-7">
        <div className="mb-3 h-1 w-12 rounded-full bg-[#EE6A4C]" />

        <h1 className="font-['Baloo_2'] text-4xl font-bold leading-tight text-[#22333B] md:text-5xl">
          {isMatchingPhase
            ? "Review your product matches"
            : "Add product details"}
        </h1>

        <p className="mt-3 max-w-2xl text-base leading-7 text-[#48605F]">
          {isMatchingPhase ? (
            <>
              We matched SKUs that look like
              the same product. Move anything
              that doesn&apos;t belong together,
              then continue when the matches
              look right.
            </>
          ) : (
            <>
              Give each product a name and
              enter how many individual units
              come in a case.
            </>
          )}
        </p>
      </div>

      {/* =================================================
          Selected Product Helper
      ================================================= */}

      {isMatchingPhase &&
        selectedProduct && (
          <div
            className="
              mb-4
              flex
              flex-wrap
              items-center
              justify-between
              gap-3
              rounded-[16px]
              border
              border-[#EE6A4C]/30
              bg-[#FBEBD3]
              px-4
              py-2.5
            "
          >
            <div className="text-sm text-[#22333B]">
              Moving{" "}
              <span className="font-bold">
                {selectedProduct.rawSku}
              </span>
            </div>

            <button
              type="button"
              onClick={() =>
                setSelectedProduct(null)
              }
              className="
                text-sm
                font-semibold
                text-[#48605F]
                transition
                hover:text-[#EE6A4C]
              "
            >
              Cancel
            </button>
          </div>
        )}

        {/* =================================================
            Product rows
        ================================================= */}

        <div className="space-y-3">
          {groups.map((group) => {
            const keheProducts = group.products.filter(
              (product) => product.source === "kehe"
            )

            const unfiProducts = group.products.filter(
              (product) => product.source === "unfi"
            )

            return (
              <div
                key={group.id}
                onDragOver={(event) => {
                  if (isMatchingPhase) {
                    event.preventDefault()
                  }
                }}
                onDrop={() => {
                  if (isMatchingPhase) {
                    handleDropOnGroup(group.id)
                  }
                }}
                onClick={() => {
                  if (isMatchingPhase) {
                    handleGroupClick(group.id)
                  }
                }}
                className={`
                  mx-auto
                  flex
                  w-full
                  items-center
                  justify-center
                  gap-3
                  border-2
                  border-[#22333B]
                  bg-[#FDFBF5]
                  shadow-[4px_4px_0_0_#ECE6D6]
                  transition-all
                  duration-500
                  ease-out

                  ${
                    isDetailsPhase
                      ? "max-w-6xl rounded-[20px] px-4 py-3"
                      : "max-w-[760px] rounded-full px-5 py-3"
                  }

                  ${
                    isMatchingPhase && selectedProduct
                      ? "cursor-pointer border-[#EE6A4C]"
                      : ""
                  }
                `}
              >
                {/* =========================================
                    Product name — expands in from left
                ========================================= */}

                <div
                  className={`
                    flex
                    shrink-0
                    justify-center
                    overflow-hidden
                    transition-all
                    duration-500
                    ease-out

                    ${
                      isDetailsPhase
                        ? "w-[180px] translate-x-0 opacity-100"
                        : "pointer-events-none w-0 translate-x-3 opacity-0"
                    }
                  `}
                  onClick={(event) =>
                    event.stopPropagation()
                  }
                >
                  <input
                    value={group.cleanSku}
                    onChange={(event) =>
                      updateCleanSku(
                        group.id,
                        event.target.value
                      )
                    }
                    placeholder="Product name"
                    className={`
                      h-10
                      w-[180px]
                      rounded-full
                      bg-white
                      px-4
                      font-['Baloo_2']
                      text-sm
                      font-bold
                      text-[#22333B]
                      outline-none
                      transition
                      placeholder:text-[#48605F]/35
                      focus:ring-2
                      focus:ring-[#EE6A4C]/10

                      ${
                        group.cleanSku.trim()
                          ? "border-2 border-[#22333B]"
                          : "border-2 border-[#EE6A4C]"
                      }
                    `}
                  />
                </div>

                {/* =========================================
                    KeHE pill
                ========================================= */}

                {hasKehe && (
                  <div className="flex min-w-0 flex-1 justify-center">
                    {keheProducts.length > 0 ? (
                      <div className="flex flex-wrap justify-center gap-1.5">
                        {keheProducts.map(
                          (product) => (
                            <ProductPill
                              key={product.id}
                              product={product}
                              selected={
                                isMatchingPhase &&
                                selectedProduct?.id ===
                                  product.id
                              }
                              interactive={
                                isMatchingPhase
                              }
                              onClick={() =>
                                handleProductClick(
                                  product
                                )
                              }
                              onDragStart={() =>
                                handleDragStart(
                                  product
                                )
                              }
                            />
                          )
                        )}
                      </div>
                    ) : isMatchingPhase ? (
                      <EmptySlot />
                    ) : (
                      <span className="text-xs text-[#48605F]/40">
                        —
                      </span>
                    )}
                  </div>
                )}

                {/* =========================================
                    Match arrow
                ========================================= */}

                {hasMultipleDistributors && (
                  <div className="shrink-0 text-sm font-bold text-[#EE6A4C]">
                    ↔
                  </div>
                )}

                {/* =========================================
                    UNFI pill
                ========================================= */}

                {hasUnfi && (
                  <div className="flex min-w-0 flex-1 justify-center">
                    {unfiProducts.length > 0 ? (
                      <div className="flex flex-wrap justify-center gap-1.5">
                        {unfiProducts.map(
                          (product) => (
                            <ProductPill
                              key={product.id}
                              product={product}
                              selected={
                                isMatchingPhase &&
                                selectedProduct?.id ===
                                  product.id
                              }
                              interactive={
                                isMatchingPhase
                              }
                              onClick={() =>
                                handleProductClick(
                                  product
                                )
                              }
                              onDragStart={() =>
                                handleDragStart(
                                  product
                                )
                              }
                            />
                          )
                        )}
                      </div>
                    ) : isMatchingPhase ? (
                      <EmptySlot />
                    ) : (
                      <span className="text-xs text-[#48605F]/40">
                        —
                      </span>
                    )}
                  </div>
                )}

                {/* =========================================
                    Units / case — expands in from right
                ========================================= */}

                <div
                  className={`
                    flex
                    shrink-0
                    justify-center
                    overflow-hidden
                    transition-all
                    duration-500
                    ease-out

                    ${
                      isDetailsPhase
                        ? "w-[180px] translate-x-0 opacity-100"
                        : "pointer-events-none w-0 translate-x-3 opacity-0"
                    }
                  `}
                  onClick={(event) =>
                    event.stopPropagation()
                  }
                >
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={group.unitsPerCase}
                    onChange={(event) =>
                      updateUnitsPerCase(
                        group.id,
                        event.target.value
                      )
                    }
                    placeholder="Units/case"
                    className={`
                      h-10
                      w-[110px]
                      appearance-none
                      rounded-full
                      bg-white
                      px-3
                      text-center
                      text-sm
                      font-bold
                      text-[#22333B]
                      outline-none
                      transition
                      placeholder:text-[11px]
                      placeholder:text-[#48605F]/35
                      focus:ring-2
                      focus:ring-[#EE6A4C]/10
                      [&::-webkit-inner-spin-button]:appearance-none
                      [&::-webkit-outer-spin-button]:appearance-none

                      ${
                        group.unitsPerCase !== "" &&
                        Number(group.unitsPerCase) > 0
                          ? "border-2 border-[#22333B]"
                          : "border-2 border-[#EE6A4C]"
                      }
                    `}
                  />
                </div>
              </div>
            )
          })}
        </div>
      {/* =================================================
          Unassigned products — matching only
      ================================================= */}

      {isMatchingPhase &&
        unassigned.length > 0 && (
          <div
            onDragOver={(event) =>
              event.preventDefault()
            }
            onDrop={
              handleDropOnUnassigned
            }
            className="
              mt-5
              rounded-[20px]
              border-2
              border-dashed
              border-[#22333B]/30
              bg-[#ECE6D6]/45
              px-4
              py-4
            "
          >
            <div
              className="
                flex
                flex-col
                gap-3
                sm:flex-row
                sm:items-center
              "
            >
              <div className="sm:w-[165px] sm:shrink-0">
                <div className="font-['Baloo_2'] text-lg font-bold text-[#22333B]">
                  Needs a home
                </div>

                <div className="text-xs text-[#48605F]">
                  Drag into a product
                </div>
              </div>

              <div className="flex flex-1 flex-wrap gap-2">
                {unassigned.map(
                  (product) => (
                    <ProductPill
                      key={product.id}
                      product={product}
                      selected={
                        selectedProduct?.id ===
                        product.id
                      }
                      interactive
                      onClick={() =>
                        handleProductClick(
                          product
                        )
                      }
                      onDragStart={() =>
                        handleDragStart(
                          product
                        )
                      }
                    />
                  )
                )}
              </div>
            </div>
          </div>
        )}

      {/* =================================================
          Create Product — matching only
      ================================================= */}

      {isMatchingPhase && (
        <button
          type="button"
          onClick={createGroup}
          className="
            mt-4
            inline-flex
            h-10
            items-center
            justify-center
            rounded-full
            border
            border-dashed
            border-[#22333B]/35
            px-4
            text-sm
            font-bold
            text-[#48605F]
            transition
            hover:border-[#EE6A4C]
            hover:text-[#EE6A4C]
          "
        >
          + Create product
        </button>
      )}

      {/* =================================================
          Footer — matching
      ================================================= */}

      {isMatchingPhase && (
        <div
          className="
            mt-7
            flex
            flex-col
            gap-4
            border-t
            border-[#22333B]/15
            pt-6
            sm:flex-row
            sm:items-center
            sm:justify-between
          "
        >
          <div>
            <div className="text-sm font-semibold text-[#22333B]">
              {populatedGroups.length}{" "}
              {populatedGroups.length ===
              1
                ? "product group"
                : "product groups"}
            </div>

            <div className="mt-0.5 text-xs text-[#48605F]">
              {unassigned.length > 0
                ? `${unassigned.length} still need to be matched`
                : "Every SKU has a product."}
            </div>
          </div>

          <button
            type="button"
            disabled={!matchingComplete}
            onClick={
              handleContinueToDetails
            }
            className="
              inline-flex
              h-12
              items-center
              justify-center
              rounded-full
              border-2
              border-[#22333B]
              bg-[#EE6A4C]
              px-7
              text-sm
              font-bold
              text-white
              shadow-[4px_4px_0_0_#22333B]
              transition
              hover:-translate-y-0.5
              hover:bg-[#D9532F]
              disabled:cursor-not-allowed
              disabled:opacity-40
              disabled:hover:translate-y-0
            "
          >
            Matches look good →
          </button>
        </div>
      )}

      {/* =================================================
          Footer — details
      ================================================= */}

      {isDetailsPhase && (
        <div
          className="
            mt-7
            flex
            flex-col
            gap-4
            border-t
            border-[#22333B]/15
            pt-6
            sm:flex-row
            sm:items-center
            sm:justify-between
          "
        >
          <div>
            <div className="text-sm font-semibold text-[#22333B]">
              {populatedGroups.length}{" "}
              {populatedGroups.length ===
              1
                ? "product"
                : "products"}
            </div>

            <div className="mt-0.5 text-xs text-[#48605F]">
              {detailsComplete
                ? "Everything looks ready."
                : "Add a name and case size for each product."}
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            {hasMultipleDistributors && (
              <button
                type="button"
                onClick={
                  handleBackToMatches
                }
                disabled={isSubmitting}
                className="
                  inline-flex
                  h-12
                  items-center
                  justify-center
                  rounded-full
                  border-2
                  border-[#22333B]
                  bg-[#FDFBF5]
                  px-6
                  text-sm
                  font-bold
                  text-[#22333B]
                  transition
                  hover:bg-[#F4F0E5]
                  disabled:cursor-not-allowed
                  disabled:opacity-40
                "
              >
                ← Back to matches
              </button>
            )}

            <button
              type="button"
              disabled={
                !detailsComplete ||
                isSubmitting
              }
              onClick={handleConfirm}
              className="
                inline-flex
                h-12
                items-center
                justify-center
                rounded-full
                border-2
                border-[#22333B]
                bg-[#EE6A4C]
                px-7
                text-sm
                font-bold
                text-white
                shadow-[4px_4px_0_0_#22333B]
                transition
                hover:-translate-y-0.5
                hover:bg-[#D9532F]
                disabled:cursor-not-allowed
                disabled:opacity-40
                disabled:hover:translate-y-0
              "
            >
              {isSubmitting
                ? "Preparing insights..."
                : "Finish & see my insights →"}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

// =========================================================
// Empty Slot
// =========================================================

function EmptySlot() {
  return (
    <div
      className="
        flex
        h-9
        min-w-[110px]
        items-center
        justify-center
        rounded-full
        border
        border-dashed
        border-[#22333B]/20
        px-3
        text-[11px]
        text-[#48605F]/50
      "
    >
      Drop SKU here
    </div>
  )
}

// =========================================================
// Product Pill
// =========================================================

function ProductPill({
  product,
  selected,
  interactive,
  onClick,
  onDragStart,
}: {
  product: ReconciliationProduct
  selected: boolean
  interactive: boolean
  onClick: () => void
  onDragStart: () => void
}) {
  return (
    <button
      type="button"
      draggable={interactive}
      onDragStart={(event) => {
        if (!interactive) return

        event.stopPropagation()
        onDragStart()
      }}
      onClick={(event) => {
        event.stopPropagation()

        if (!interactive) return

        onClick()
      }}
      title={
        product.rawUpc
          ? `UPC ${product.rawUpc}`
          : undefined
      }
      className={`
        max-w-full
        rounded-full
        border
        px-3
        py-1.5
        text-left
        text-xs
        font-semibold
        leading-4
        transition

        ${
          interactive
            ? "cursor-grab active:cursor-grabbing hover:-translate-y-0.5 hover:border-[#EE6A4C]"
            : "cursor-default"
        }

        ${
          selected
            ? `
                border-[#EE6A4C]
                bg-[#EE6A4C]
                text-white
                shadow-[2px_2px_0_0_#22333B]
              `
            : `
                border-[#22333B]/40
                bg-[#F4F0E5]
                text-[#22333B]
              `
        }
      `}
    >
      {product.rawSku}
    </button>
  )
}