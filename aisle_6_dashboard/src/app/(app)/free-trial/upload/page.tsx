"use client"

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"
import { ArrowLeft, ArrowRight, Check, Database } from "lucide-react"

import { useOrg } from "@/components/OrgContext"
import SKUReconciliation, {
  ReconciliationGroup,
  ReconciliationProduct,
} from "@/components/onboarding/SKUReconciliation"
import DistributorDataUploadCard from "@/components/ui/DistributorDataUploadCard"
import { supabase } from "@/lib/supabase"
import { useRouter } from "next/navigation"
import ExportGuide, {ExportGuideStep} from "@/components/onboarding/ExportGuide"

// =========================================================
// Theme
// =========================================================

const theme = {
  cream: "#F4F0E5",
  creamDeep: "#ECE6D6",
  paper: "#FDFBF5",

  coral: "#EE6A4C",
  coralDark: "#D9532F",

  ink: "#22333B",
  slate: "#48605F",

  sageBg: "#E3EFD9",
  sageInk: "#3E7A46",

  amberBg: "#FBEBD3",
  amberInk: "#B0762B",
}


// =========================================================
// Types
// =========================================================

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

type PageStep =
  | "upload"
  | "reconciliation"

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
// Date helpers
// =========================================================

function getLastCompletedMonth() {
  const now = new Date()

  return new Date(
    now.getFullYear(),
    now.getMonth() - 1,
    1
  )
}

function monthToItem(
  date: Date
): MonthItem {
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

  const start = new Date(
    `${startDate}T00:00:00`
  )

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
    months.push(
      monthToItem(current)
    )

    current = new Date(
      current.getFullYear(),
      current.getMonth() + 1,
      1
    )
  }

  return months
}

function buildTrailingMonths(
  count: number
): MonthItem[] {
  const end = getLastCompletedMonth()

  const start = new Date(
    end.getFullYear(),
    end.getMonth() - (count - 1),
    1
  )

  const months: MonthItem[] = []

  let current = start

  while (current <= end) {
    months.push(
      monthToItem(current)
    )

    current = new Date(
      current.getFullYear(),
      current.getMonth() + 1,
      1
    )
  }

  return months
}

function formatRange(
  months: MonthItem[]
) {
  if (!months.length) return ""

  const first = months[0]
  const last =
    months[months.length - 1]

  return `${first.label} ${first.year} – ${last.label} ${last.year}`
}

// =========================================================
// Reconciliation helpers
// =========================================================

function makeProductId(
  product: BackendProduct
) {
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
  return payload.suggested_matches.map(
    (match) => ({
      id: `match-${match.normalized_upc}`,
      cleanSku: "",
      unitsPerCase: "",
      products:
        match.products.map(
          toFrontendProduct
        ),
    })
  )
}

function buildUnassignedProducts(
  payload: ReconciliationPayload
): ReconciliationProduct[] {
  return payload.unmatched_products.map(
    toFrontendProduct
  )
}

// =========================================================
// Reconciliation step
// =========================================================

function ReconciliationStep({
  orgId,
  apiBaseUrl,
  onBack,
}: {
  orgId: string
  apiBaseUrl: string
  onBack: () => void
}) {
  const router = useRouter()

  const [groups, setGroups] =
    useState<ReconciliationGroup[]>([])

  const [
    unassigned,
    setUnassigned,
  ] = useState<
    ReconciliationProduct[]
  >([])

  const [loading, setLoading] =
    useState(true)

  const [
    isSubmitting,
    setIsSubmitting,
  ] = useState(false)

  const [error, setError] =
    useState<string | null>(null)


  // -------------------------------------------------------
  // Load reconciliation
  // -------------------------------------------------------

  useEffect(() => {
    async function loadReconciliation() {
      try {
        setLoading(true)
        setError(null)

        const response =
          await fetch(
            `${apiBaseUrl}/onboarding/sku-reconciliation?org_id=${encodeURIComponent(
              orgId
            )}`
          )

        if (!response.ok) {
          const body =
            await response
              .json()
              .catch(() => null)

          throw new Error(
            body?.detail ||
              `Failed to load product matching (${response.status})`
          )
        }

        const payload: ReconciliationPayload =
          await response.json()

        setGroups(
          buildInitialGroups(
            payload
          )
        )

        setUnassigned(
          buildUnassignedProducts(
            payload
          )
        )
      } catch (err) {
        console.error(err)

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load your products."
        )
      } finally {
        setLoading(false)
      }
    }

    loadReconciliation()
  }, [apiBaseUrl, orgId])

  // -------------------------------------------------------
  // Save reconciliation
  // -------------------------------------------------------

  async function handleConfirm(
    confirmedGroups: ReconciliationGroup[]
  ) {
    try {
      setIsSubmitting(true)
      setError(null)

      // -------------------------------------------------------
      // 1. Save SKU reconciliation
      // -------------------------------------------------------

      const reconciliationResponse =
        await fetch(
          `${apiBaseUrl}/onboarding/sku-reconciliation`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              org_id: orgId,
              groups: confirmedGroups,
            }),
          }
        )

      if (!reconciliationResponse.ok) {
        const body =
          await reconciliationResponse
            .json()
            .catch(() => null)

        throw new Error(
          body?.detail ||
            `Failed to save product matching (${reconciliationResponse.status})`
        )
      }

      const reconciliationResult =
        await reconciliationResponse.json()

      console.log(
        "Saved SKU reconciliation:",
        reconciliationResult
      )

      // -------------------------------------------------------
      // 2. Process distributor data
      // -------------------------------------------------------

      const processResponse =
        await fetch(
          `${apiBaseUrl}/free-trial/process?org_id=${encodeURIComponent(
            orgId
          )}`,
          {
            method: "POST",
          }
        )

      const processResult =
        await processResponse
          .json()
          .catch(() => null)

      if (!processResponse.ok) {
        throw new Error(
          processResult?.detail ||
            `Failed to process distributor data (${processResponse.status})`
        )
      }

      if (processResult?.status !== "ready") {
        throw new Error(
          "Processing completed without returning a ready status."
        )
      }

      console.log(
        "Free trial processing complete:",
        processResult
      )

      // -------------------------------------------------------
      // 3. Analysis is ready — continue
      // -------------------------------------------------------

      router.push("/free-trial")
    } catch (err) {
      console.error(
        "Free trial setup failed:",
        err
      )

      setError(
        err instanceof Error
          ? err.message
          : "Failed to prepare your analysis."
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  // -------------------------------------------------------
  // Loading state
  // -------------------------------------------------------

  if (loading) {
    return (
      <main className="min-h-screen bg-[#F4F0E5] px-5 py-10 md:px-8 md:py-14">
        <div className="mx-auto max-w-6xl">
          <button
            type="button"
            onClick={onBack}
            className="
              mb-10
              inline-flex
              items-center
              gap-2
              text-sm
              font-semibold
              text-[#48605F]
              transition
              hover:text-[#22333B]
            "
          >
            <ArrowLeft
              size={16}
            />
            Back to uploads
          </button>

          <div
            className="
              rounded-[28px]
              border-2
              border-[#22333B]
              bg-[#FDFBF5]
              px-7
              py-10
              shadow-[7px_7px_0_0_#ECE6D6]
              md:px-10
            "
          >
            <div
              className="
                mb-5
                flex
                h-11
                w-11
                items-center
                justify-center
                rounded-full
                bg-[#EE6A4C]/10
                text-[#EE6A4C]
              "
            >
              <Database
                size={20}
              />
            </div>

            <h1
              className="
                font-['Baloo_2']
                text-3xl
                font-bold
                tracking-[-0.03em]
                text-[#22333B]
              "
            >
              Matching your
              products...
            </h1>

            <p className="mt-2 text-sm leading-6 text-[#48605F]">
              We&apos;re finding
              the same products
              across your
              distributor files.
            </p>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[#F4F0E5] px-5 py-10 md:px-8 md:py-14">
      <div className="mx-auto max-w-6xl">
        {/* Back */}

        <button
          type="button"
          onClick={onBack}
          className="
            mb-7
            inline-flex
            items-center
            gap-2
            text-sm
            font-semibold
            text-[#48605F]
            transition
            hover:text-[#22333B]
          "
        >
          <ArrowLeft
            size={16}
          />
          Back to uploads
        </button>

        {/* Progress */}

        <div className="mb-8 flex items-center gap-3">
          {/* Step 1 — complete */}
          <div className="flex items-center gap-2">
            <div
              className="
                flex
                h-8
                w-8
                items-center
                justify-center
                rounded-full
                bg-[#E3EFD9]
                text-[#3E7A46]
              "
            >
              <Check size={16} />
            </div>

            <span className="text-sm font-semibold text-[#22333B]">
              Uploads
            </span>
          </div>

          {/* Connector */}
          <div className="h-[2px] w-10 bg-[#EE6A4C]" />

          {/* Step 2 — current */}
          <div className="flex items-center gap-2">
            <div
              className="
                flex
                h-8
                w-8
                items-center
                justify-center
                rounded-full
                bg-[#EE6A4C]
                text-xs
                font-bold
                text-white
              "
            >
              2
            </div>

            <span className="text-sm font-semibold text-[#22333B]">
              Review products
            </span>
          </div>

          {/* Connector */}
          <div className="h-[2px] w-10 bg-[#D8D2C7]" />

          {/* Step 3 — upcoming */}
          <div className="flex items-center gap-2 opacity-55">
            <div
              className="
                flex
                h-8
                w-8
                items-center
                justify-center
                rounded-full
                border
                border-[#B9B2A6]
                text-xs
                font-bold
                text-[#48605F]
              "
            >
              3
            </div>

            <span className="text-sm font-semibold text-[#48605F]">
              Insights
            </span>
          </div>
        </div>

        {/* Error */}

        {error && (
          <div
            className="
              mb-5
              rounded-[18px]
              border
              border-[#EE6A4C]
              bg-[#FBEBD3]
              px-5
              py-4
              text-sm
              font-semibold
              text-[#22333B]
            "
          >
            {error}
          </div>
        )}

        {/* Existing reusable component */}

        <SKUReconciliation
          initialGroups={groups}
          initialUnassigned={
            unassigned
          }
          onConfirm={
            handleConfirm
          }
          isSubmitting={
            isSubmitting
          }
        />

      </div>
    </main>
  )
}

// =========================================================
// Main page
// =========================================================

export default function FreeTrialUploadPage() {
  const { org } = useOrg()

  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    ""

  const [step, setStep] =
    useState<PageStep>("upload")

  const [
    distributors,
    setDistributors,
  ] = useState<
    OrgDistributor[]
  >([])

  const [
    uploadedKeheMonths,
    setUploadedKeheMonths,
  ] = useState<Set<string>>(
    new Set()
  )

  const [
    uploadedUnfiMonths,
    setUploadedUnfiMonths,
  ] = useState<Set<string>>(new Set())

  const [loading, setLoading] =
    useState(true)


  // =======================================================
  // Distributor setup
  // =======================================================

  const kehe =
    distributors.find(
      (row) =>
        row.distributor.toLowerCase() ===
        "kehe"
    )

  const unfi =
    distributors.find(
      (row) =>
        row.distributor.toLowerCase() ===
        "unfi"
    )

  // =======================================================
  // KeHE history logic
  // =======================================================

  const fullKeheHistory =
    useMemo(
      () =>
        buildMonthsFromStart(
          kehe?.start_date ??
            null
        ),
      [kehe?.start_date]
    )

  const completedHistoryMonths =
    fullKeheHistory.length

  const isNewBrand =
    completedHistoryMonths >
      0 &&
    completedHistoryMonths <
      6

  const trailing6Months =
    useMemo(
      () =>
        buildTrailingMonths(
          6
        ),
      []
    )

  const requiredMonths =
    isNewBrand
      ? fullKeheHistory
      : trailing6Months

  const requiredUploadedCount =
    requiredMonths.filter(
      (month) =>
        uploadedKeheMonths.has(
          month.key
        )
    ).length

  const hasAllRequiredMonths =
    requiredMonths.length >
      0 &&
    requiredMonths.every(
      (month) =>
        uploadedKeheMonths.has(
          month.key
        )
    )

  // =======================================================
  // UNFI history logic
  // =======================================================

  const fullUnfiHistory = useMemo(
    () =>
      buildMonthsFromStart(
        unfi?.start_date ?? null
      ),
    [unfi?.start_date]
  )

  const unfiCompletedHistoryMonths =
    fullUnfiHistory.length

  const isNewUnfiBrand =
    unfiCompletedHistoryMonths > 0 &&
    unfiCompletedHistoryMonths < 6

  const requiredUnfiMonths =
    isNewUnfiBrand
      ? fullUnfiHistory
      : trailing6Months

  const requiredUnfiUploadedCount =
    requiredUnfiMonths.filter((month) =>
      uploadedUnfiMonths.has(month.key)
    ).length

  const hasAllRequiredUnfiMonths =
    requiredUnfiMonths.length > 0 &&
    requiredUnfiMonths.every((month) =>
      uploadedUnfiMonths.has(month.key)
    )

  const hasAllRequiredDistributorMonths =
    (!kehe || hasAllRequiredMonths) &&
    (!unfi || hasAllRequiredUnfiMonths)

  // =======================================================
  // KeHE coverage
  // =======================================================

  const refreshKeheCoverage =
    useCallback(async () => {
      if (!org?.id) return

      const {
        data,
        error,
      } =
        await supabase
          .from(
            "org_distributor_months"
          )
          .select("month")
          .eq(
            "org_id",
            org.id
          )
          .eq(
            "distributor",
            "kehe"
          )
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
          (data ?? []).map(
            (row) =>
              row.month.slice(
                0,
                7
              )
          )
        )
      )
    }, [org?.id])

    const refreshUnfiCoverage =
  useCallback(async () => {
    if (!org?.id) return

    const { data, error } =
      await supabase
        .from("org_distributor_months")
        .select("month")
        .eq("org_id", org.id)
        .eq("distributor", "unfi")
        .order("month")

    if (error) {
      console.error(
        "Failed to load UNFI coverage:",
        error
      )
      return
    }

    setUploadedUnfiMonths(
      new Set(
        (data ?? []).map((row) =>
          row.month.slice(0, 7)
        )
      )
    )
  }, [org?.id])

  // =======================================================
  // Initial page load
  // =======================================================

  useEffect(() => {
    if (!org?.id) return

    async function loadPage() {
      setLoading(true)

      const {
        data,
        error,
      } =
        await supabase
          .from(
            "org_distributors"
          )
          .select(
            "distributor, start_date, is_supported"
          )
          .eq(
            "org_id",
            org!.id
          )

      if (error) {
        console.error(
          "Failed to load distributors:",
          error
        )

        setLoading(false)
        return
      }

      setDistributors(
        data ?? []
      )

      await Promise.all([
        refreshKeheCoverage(),
        refreshUnfiCoverage(),
      ])

      setLoading(false)
    }

    loadPage()
  }, [
    org?.id,
    refreshKeheCoverage,
    refreshUnfiCoverage
  ])

  // =======================================================
  // Loading
  // =======================================================

  if (
    !org?.id ||
    loading
  ) {
    return (
      <main className="min-h-screen bg-[#F4F0E5] px-6 py-16">
        <div className="mx-auto max-w-6xl">
          <p className="font-['Baloo_2'] text-xl font-bold text-[#22333B]">
            Getting your
            uploads ready...
          </p>

          <p className="mt-1 text-sm text-[#48605F]">
            Loading your
            distributor setup.
          </p>
        </div>
      </main>
    )
  }

  // =======================================================
  // Step 2 — SKU reconciliation
  // =======================================================

  if (
    step ===
    "reconciliation"
  ) {
    return (
      <ReconciliationStep
        orgId={org.id}
        apiBaseUrl={
          apiBaseUrl
        }
        onBack={() =>
          setStep("upload")
        }
      />
    )
  }

  // =======================================================
  // Step 1 — Upload
  // =======================================================

  return (
    <main className="min-h-screen bg-[#F4F0E5] px-5 py-10 md:px-8 md:py-14">
      <div className="mx-auto max-w-6xl">
        {/* =================================================
            Header
        ================================================= */}

        <div className="mb-10">
          <div
            className="
              mb-4
              inline-flex
              items-center
              gap-2
              rounded-full
              border
              border-[#22333B]/10
              bg-[#FDFBF5]
              px-3
              py-1.5
              text-[11px]
              font-bold
              uppercase
              tracking-[0.14em]
              text-[#48605F]
            "
          >
            <span className="h-2 w-2 rounded-full bg-[#EE6A4C]" />
            Your free analysis
          </div>

          <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:gap-10">
            <h1
              className="
                shrink-0
                font-['Baloo_2']
                text-4xl
                font-bold
                leading-[0.98]
                tracking-[-0.04em]
                text-[#22333B]
                md:text-5xl
                xl:text-[58px]
              "
            >
              Upload your distributor data
            </h1>

            <div className="hidden h-14 w-px bg-[#22333B]/10 xl:block" />

            <p
              className="
                max-w-xl
                text-[16px]
                leading-6
                text-[#48605F]
              "
            >
              Upload your recent distributor reports. We&apos;ll match your
              products before SKUba analyzes anything.
            </p>
          </div>
        </div>

        {/* =================================================
            Progress
        ================================================= */}

        <div className="mb-8 flex items-center gap-3">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#E3EFD9] text-[#3E7A46]">
                ✓
              </div>
              <span className="font-semibold text-[#22333B]">
                Uploads
              </span>
            </div>

            <div className="h-[2px] w-12 bg-[#EE6A4C]" />

            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#EE6A4C] font-semibold text-white">
                2
              </div>
              <span className="font-semibold text-[#22333B]">
                Review products
              </span>
            </div>

            <div className="h-[2px] w-12 bg-[#D8D2C7]" />

            <div className="flex items-center gap-3 opacity-60">
              <div className="flex h-9 w-9 items-center justify-center rounded-full border border-[#B9B2A6] font-semibold text-[#48605F]">
                3
              </div>
              <span className="font-semibold text-[#48605F]">
                Insights
              </span>
            </div>
          </div>
        </div>  
        <div className="space-y-6">
          {/* =================================================
              KeHE
          ================================================= */}

          {kehe && (
            <section
              className="
                overflow-hidden
                rounded-[28px]
                border-2
                border-[#22333B]
                bg-[#FDFBF5]
                shadow-[7px_7px_0_0_#ECE6D6]
              "
            >
              {/* Top */}

              <div className="px-6 py-6 md:px-8 md:py-8">
                <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <div
                        className="
                          flex
                          h-10
                          w-10
                          items-center
                          justify-center
                          rounded-full
                          bg-[#EE6A4C]/10
                          text-[#EE6A4C]
                        "
                      >
                        <Database
                          size={18}
                        />
                      </div>

                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#48605F]">
                          Distributor
                        </p>

                        <p className="font-['Baloo_2'] text-lg font-bold text-[#22333B]">
                          KeHE
                        </p>
                      </div>
                    </div>

                    <h2
                      className="
                        mt-6
                        font-['Baloo_2']
                        text-[28px]
                        font-bold
                        leading-tight
                        tracking-[-0.03em]
                        text-[#22333B]
                      "
                    >
                      {isNewBrand
                        ? "Upload your complete KeHE history"
                        : "Upload your latest 6 completed months"}
                    </h2>

                    <p className="mt-2 max-w-2xl text-[14px] leading-6 text-[#48605F]">
                      {isNewBrand
                        ? "Because you started with KeHE recently, your complete history is all we need to get started."
                        : "Add one monthly KeHE report at a time. We'll keep track of what's here and what's still missing."}
                    </p>
                  </div>

                  {requiredMonths.length >
                    0 && (
                    <div
                      className="
                        shrink-0
                        rounded-full
                        border
                        border-[#22333B]/10
                        bg-[#F4F0E5]
                        px-4
                        py-2
                        text-xs
                        font-bold
                        text-[#22333B]
                      "
                    >
                      {formatRange(
                        requiredMonths
                      )}
                    </div>
                  )}
                </div>

      {/* =================================================
          Upload + progress + help
      ================================================= */}

      <div className="mt-6 space-y-4">

        {/* -----------------------------------------------
            1. Primary action — Upload
        ----------------------------------------------- */}

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#EE6A4C]">
              Add data
            </p>

            <p className="text-xs font-medium text-[#48605F]">
              One completed month per report
            </p>
          </div>

          <DistributorDataUploadCard
            distributor="kehe"
            apiBaseUrl={apiBaseUrl}
            uploadMode="free-trial"
            onUploadSuccess={refreshKeheCoverage}
          />
        </div>

        {/* -----------------------------------------------
            2. Required history
        ----------------------------------------------- */}

        {requiredMonths.length > 0 && (
          <div
            className="
              rounded-[20px]
              border
              border-[#22333B]/10
              bg-[#F4F0E5]
              px-5
              py-4
            "
          >
            {/* Status row */}

            <div className="flex items-center justify-between gap-4">
              <div className="flex items-baseline gap-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#48605F]">
                  Required history
                </p>

                <p className="font-['Baloo_2'] text-base font-bold text-[#22333B]">
                  {hasAllRequiredMonths
                    ? "Everything we need is here"
                    : `${requiredUploadedCount} of ${requiredMonths.length} months uploaded`}
                </p>
              </div>

              <div
                className={`
                  shrink-0
                  rounded-full
                  px-3
                  py-1
                  text-[11px]
                  font-bold
                  ${
                    hasAllRequiredMonths
                      ? "bg-[#E3EFD9] text-[#3E7A46]"
                      : "bg-[#FBEBD3] text-[#B0762B]"
                  }
                `}
              >
                {hasAllRequiredMonths
                  ? "Ready"
                  : `${
                      requiredMonths.length -
                      requiredUploadedCount
                    } remaining`}
              </div>
            </div>

            {/* Progress bar */}

            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#ECE6D6]">
              <div
                className="
                  h-full
                  rounded-full
                  bg-[#EE6A4C]
                  transition-all
                "
                style={{
                  width: `${Math.round(
                    (requiredUploadedCount /
                      requiredMonths.length) *
                      100
                  )}%`,
                }}
              />
            </div>

            {/* Compact month tiles */}

            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              {requiredMonths.map((month) => {
                const uploaded =
                  uploadedKeheMonths.has(month.key)

                return (
                  <div
                    key={month.key}
                    className={`
                      flex
                      items-center
                      justify-between
                      rounded-[14px]
                      border
                      px-3
                      py-3
                      ${
                        uploaded
                          ? "border-[#3E7A46]/25 bg-[#E3EFD9]"
                          : "border-[#22333B]/10 bg-[#FDFBF5]"
                      }
                    `}
                  >
                    <div>
                      <p className="font-['Baloo_2'] text-base font-bold leading-none text-[#22333B]">
                        {month.label}
                      </p>

                      <p className="mt-1 text-[10px] font-medium text-[#48605F]">
                        {month.year}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <p
                        className={`
                          text-[10px]
                          font-bold
                          ${
                            uploaded
                              ? "text-[#3E7A46]"
                              : "text-[#48605F]/50"
                          }
                        `}
                      >
                        {uploaded
                          ? "Uploaded"
                          : "Needed"}
                      </p>

                      <span
                        className={`
                          h-2
                          w-2
                          shrink-0
                          rounded-full
                          ${
                            uploaded
                              ? "bg-[#3E7A46]"
                              : "bg-[#ECE6D6]"
                          }
                        `}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* -----------------------------------------------
            3. Help — intentionally hard to miss
        ----------------------------------------------- */}


                </div>
              </div>
            </section>
          )}

          {/* =================================================
              UNFI
          ================================================= */}

          {unfi && (
            <section
              className="
                overflow-hidden
                rounded-[28px]
                border-2
                border-[#22333B]
                bg-[#FDFBF5]
                shadow-[7px_7px_0_0_#ECE6D6]
              "
            >
              <div className="px-6 py-6 md:px-8 md:py-8">
                {/* Header */}

                <div className="flex items-center gap-3">
                  <div
                    className="
                      flex
                      h-10
                      w-10
                      items-center
                      justify-center
                      rounded-full
                      bg-[#EE6A4C]/10
                      text-[#EE6A4C]
                    "
                  >
                    <Database size={18} />
                  </div>

                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-[#48605F]">
                      Distributor
                    </p>

                    <p className="font-['Baloo_2'] text-lg font-bold text-[#22333B]">
                      UNFI
                    </p>
                  </div>
                </div>

                <h2
                  className="
                    mt-6
                    font-['Baloo_2']
                    text-[28px]
                    font-bold
                    leading-tight
                    tracking-[-0.03em]
                    text-[#22333B]
                  "
                >
                  Upload your UNFI reports
                </h2>

                <p className="mt-2 max-w-2xl text-[14px] leading-6 text-[#48605F]">
                  Export one completed month at a time from UNFI Insights and upload it here.
                </p>

                {/* Upload + help */}

                <div className="mt-6 space-y-4">
                  <div>
                    <div className="mb-2 flex items-center justify-between">
                      <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#EE6A4C]">
                        Add data
                      </p>

                      <p className="text-xs font-medium text-[#48605F]">
                        One completed month per report
                      </p>
                    </div>

                    <DistributorDataUploadCard
                      distributor="unfi"
                      apiBaseUrl={apiBaseUrl}
                      uploadMode="free-trial"
                      onUploadSuccess={refreshUnfiCoverage}
                    />
                  </div>

                  {requiredUnfiMonths.length > 0 && (
                    <div
                      className="
                        rounded-[20px]
                        border
                        border-[#22333B]/10
                        bg-[#F4F0E5]
                        px-5
                        py-4
                      "
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-baseline gap-3">
                          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#48605F]">
                            Required history
                          </p>

                          <p className="font-['Baloo_2'] text-base font-bold text-[#22333B]">
                            {hasAllRequiredUnfiMonths
                              ? "Everything we need is here"
                              : `${requiredUnfiUploadedCount} of ${requiredUnfiMonths.length} months uploaded`}
                          </p>
                        </div>

                        <div
                          className={`
                            shrink-0
                            rounded-full
                            px-3
                            py-1
                            text-[11px]
                            font-bold
                            ${
                              hasAllRequiredUnfiMonths
                                ? "bg-[#E3EFD9] text-[#3E7A46]"
                                : "bg-[#FBEBD3] text-[#B0762B]"
                            }
                          `}
                        >
                          {hasAllRequiredUnfiMonths
                            ? "Ready"
                            : `${
                                requiredUnfiMonths.length -
                                requiredUnfiUploadedCount
                              } remaining`}
                        </div>
                      </div>

                      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#ECE6D6]">
                        <div
                          className="
                            h-full
                            rounded-full
                            bg-[#EE6A4C]
                            transition-all
                          "
                          style={{
                            width: `${Math.round(
                              (requiredUnfiUploadedCount /
                                requiredUnfiMonths.length) *
                                100
                            )}%`,
                          }}
                        />
                      </div>

                      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                        {requiredUnfiMonths.map((month) => {
                          const uploaded =
                            uploadedUnfiMonths.has(month.key)

                          return (
                            <div
                              key={month.key}
                              className={`
                                flex
                                items-center
                                justify-between
                                rounded-[14px]
                                border
                                px-3
                                py-3
                                ${
                                  uploaded
                                    ? "border-[#3E7A46]/25 bg-[#E3EFD9]"
                                    : "border-[#22333B]/10 bg-[#FDFBF5]"
                                }
                              `}
                            >
                              <div>
                                <p className="font-['Baloo_2'] text-base font-bold leading-none text-[#22333B]">
                                  {month.label}
                                </p>

                                <p className="mt-1 text-[10px] font-medium text-[#48605F]">
                                  {month.year}
                                </p>
                              </div>

                              <div className="flex items-center gap-2">
                                <p
                                  className={`
                                    text-[10px]
                                    font-bold
                                    ${
                                      uploaded
                                        ? "text-[#3E7A46]"
                                        : "text-[#48605F]/50"
                                    }
                                  `}
                                >
                                  {uploaded
                                    ? "Uploaded"
                                    : "Needed"}
                                </p>

                                <span
                                  className={`
                                    h-2
                                    w-2
                                    shrink-0
                                    rounded-full
                                    ${
                                      uploaded
                                        ? "bg-[#3E7A46]"
                                        : "bg-[#ECE6D6]"
                                    }
                                  `}
                                />
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </section>
          )}
        </div>

        {/* =================================================
            Continue
        ================================================= */}

        {(kehe || unfi) && (
          <div className="mt-8">
            <div
              className="
                flex
                flex-col
                gap-5
                rounded-[24px]
                border
                border-[#22333B]/10
                bg-[#FDFBF5]
                p-5
                md:flex-row
                md:items-center
                md:justify-between
                md:px-6
              "
            >
              <div>
                <p className="font-['Baloo_2'] text-lg font-bold text-[#22333B]">
                  {hasAllRequiredDistributorMonths
                    ? "Your uploads are ready."
                    : "Finish your required uploads."}
                </p>

                <p className="mt-1 text-sm leading-5 text-[#48605F]">
                  {hasAllRequiredDistributorMonths
                    ? "Next, we'll make sure the same products are matched correctly across your distributor files."
                    : "Once every required month is here, you can continue to product matching."}
                </p>
              </div>

              <button
                type="button"
                disabled={!hasAllRequiredDistributorMonths}
                onClick={() =>
                  setStep("reconciliation")
                }
                className="
                  inline-flex
                  shrink-0
                  items-center
                  justify-center
                  gap-2
                  rounded-full
                  bg-[#EE6A4C]
                  px-6
                  py-3
                  text-sm
                  font-bold
                  text-white
                  transition
                  hover:bg-[#D9532F]
                  disabled:cursor-not-allowed
                  disabled:opacity-35
                "
              >
                Match my products
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}