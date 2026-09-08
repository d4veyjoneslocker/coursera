"use client"

import { useEffect, useState } from "react"

import SKUReconciliation, {
  ReconciliationGroup,
  ReconciliationProduct,
} from "@/components/onboarding/SKUReconciliation"

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"

// =========================================================
// TEMPORARY TEST ORG
// =========================================================

// Replace this with the same FroCo org ID
// you've been using for the backend test.
const ORG_ID = "0db03f67-b13b-438a-ab92-f808ca544ff8"

// =========================================================
// Backend response types
// =========================================================

type BackendProduct = {
  source: "kehe" | "unfi"
  raw_sku: string
  raw_upc: string | null
}

type BackendMatch = {
  match_type: string
  confidence: string
  normalized_upc: string
  products: BackendProduct[]
}

type ReconciliationPayload = {
  products: BackendProduct[]
  suggested_matches: BackendMatch[]
  unmatched_products: BackendProduct[]
}

// =========================================================
// Helpers
// =========================================================

function makeProductId(product: BackendProduct) {
  return `${product.source}-${product.raw_upc ?? "no-upc"}-${product.raw_sku}`
}

function toFrontendProduct(
  product: BackendProduct
): ReconciliationProduct {
  return {
    id: makeProductId(product),
    source: product.source,
    rawSku: product.raw_sku,
    rawUpc: product.raw_upc,
  }
}

function buildInitialGroups(
  payload: ReconciliationPayload
): ReconciliationGroup[] {
  return payload.suggested_matches.map((match) => ({
    id: `match-${match.normalized_upc}`,

    // User defines these during reconciliation.
    cleanSku: "",
    unitsPerCase: "",

    products: match.products.map(toFrontendProduct),
  }))
}

function buildUnassignedProducts(
  payload: ReconciliationPayload
): ReconciliationProduct[] {
  return payload.unmatched_products.map(toFrontendProduct)
}

// =========================================================
// Page
// =========================================================

export default function SKUReconciliationTestPage() {
  const [groups, setGroups] =
    useState<ReconciliationGroup[]>([])

  const [unassigned, setUnassigned] =
    useState<ReconciliationProduct[]>([])

  const [loading, setLoading] =
    useState(true)

  const [isSubmitting, setIsSubmitting] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)

  const [saved, setSaved] =
    useState(false)

  // =======================================================
  // Load reconciliation
  // =======================================================

  useEffect(() => {
    async function loadReconciliation() {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch(
          `${API_BASE_URL}/onboarding/sku-reconciliation?org_id=${encodeURIComponent(
            ORG_ID
          )}`
        )

        if (!response.ok) {
          throw new Error(
            `Failed to load reconciliation (${response.status})`
          )
        }

        const payload: ReconciliationPayload =
          await response.json()

        setGroups(
          buildInitialGroups(payload)
        )

        setUnassigned(
          buildUnassignedProducts(payload)
        )
      } catch (err) {
        console.error(err)

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load SKU reconciliation"
        )
      } finally {
        setLoading(false)
      }
    }

    loadReconciliation()
  }, [])

  // =======================================================
  // Save reconciliation
  // =======================================================

  async function handleConfirm(
    confirmedGroups: ReconciliationGroup[]
  ) {
    try {
      setIsSubmitting(true)
      setError(null)
      setSaved(false)

      const response = await fetch(
        `${API_BASE_URL}/onboarding/sku-reconciliation`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            org_id: ORG_ID,
            groups: confirmedGroups,
          }),
        }
      )

      if (!response.ok) {
        const errorBody =
          await response
            .json()
            .catch(() => null)

        throw new Error(
          errorBody?.detail ||
            `Failed to save reconciliation (${response.status})`
        )
      }

      const result = await response.json()

      console.log(
        "Saved reconciliation:",
        result
      )

      setSaved(true)
    } catch (err) {
      console.error(err)

      setError(
        err instanceof Error
          ? err.message
          : "Failed to save SKU reconciliation"
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  // =======================================================
  // Loading
  // =======================================================

  if (loading) {
    return (
      <main className="min-h-screen bg-[#F4F0E5] px-5 py-10 md:px-8 md:py-14">
        <div className="mx-auto max-w-5xl">
          <div className="font-['Baloo_2'] text-xl font-bold text-[#22333B]">
            Matching your products...
          </div>

          <p className="mt-1 text-sm text-[#48605F]">
            Looking for the same products across your
            distributor files.
          </p>
        </div>
      </main>
    )
  }

  // =======================================================
  // Reconciliation
  // =======================================================

  return (
    <main className="min-h-screen bg-[#F4F0E5] px-5 py-10 md:px-8 md:py-14">
      <div className="mx-auto max-w-5xl">

        {/* Error */}

        {error && (
          <div
            className="
              mb-5
              rounded-[16px]
              border
              border-[#EE6A4C]
              bg-[#FBEBD3]
              px-4
              py-3
              text-sm
              font-semibold
              text-[#22333B]
            "
          >
            {error}
          </div>
        )}

        {/* Success */}

        {saved && (
          <div
            className="
              mb-5
              rounded-[16px]
              border
              border-[#3E7A46]/30
              bg-[#E3EFD9]
              px-4
              py-3
              text-sm
              font-semibold
              text-[#3E7A46]
            "
          >
            Products saved successfully.
          </div>
        )}

        {/* Reconciliation */}

        <SKUReconciliation
          initialGroups={groups}
          initialUnassigned={unassigned}
          onConfirm={handleConfirm}
          isSubmitting={isSubmitting}
        />
      </div>
    </main>
  )
}