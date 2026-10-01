"use client"

import { useRef, useState } from "react"
import { useOrg } from "@/components/OrgContext"

type Distributor = "kehe" | "unfi"

type DistributorDataUploadCardProps = {
  distributor: Distributor
  apiBaseUrl: string
  uploadMode?: "free-trial" | "standard"
  onUploadSuccess?: () => void
}

type ExportGuideStep = {
  title: string
  description: React.ReactNode
  image: string
}

const theme = {
  blue: "#92B9DC",
  gold: "#F7B045",
  brown: "#705C4F",
  charcoal: "#343332",
  line: "#E5DDD0",
  muted: "#7A746B",
  surface: "#F8F4EC",
  greenBg: "#EAF6EE",
  greenText: "#2E7D32",
  redBg: "#FDECEC",
  redText: "#B42318",
  coral: "#EE6A4C",
}

const monthNames = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
]

const keheGuideSteps: ExportGuideStep[] = [
  {
    title: "Log in to KeHE Connect",
    description: (
      <>
        Open{" "}
        <a
          href="https://connectsupplier.kehe.com/"
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-[#EE6A4C] underline underline-offset-2"
        >
          KeHE Connect
        </a>{" "}
        and sign in to your supplier account.
      </>
    ),
    image: "/guides/kehe-upload/step-1.png",
  },
  {
    title: "Open Reporting tab",
    description:
      "From the top menu, go to KeHE CONNECT BI → Connect Data → Reporting.",
    image: "/guides/kehe-upload/step-2.png",
  },
  {
    title: "Select the Full POD Vendor report",
    description:
      "Open the Report dropdown and select KeHE Full POD Vendor.",
    image: "/guides/kehe-upload/step-3.png",
  },
  {
    title: "Select the supplier name and month",
    description:
      "In the Enterprise Supplier dropdown, select your brand. Choose the Calendar Year and Calendar Month you want to upload. Select one completed month at a time.",
    image: "/guides/kehe-upload/step-4.png",
  },
  {
    title: "Run and export the report",
    description:
      "Click View Report, then use the export menu to download the report as CSV (comma delimited).",
    image: "/guides/kehe-upload/step-5.png",
  },
]

const unfiGuideSteps: ExportGuideStep[] = [
  {
    title: "Log in to UNFI Insights",
    description: (
      <>
        Open{" "}
        <a
          href="https://platform.gocrisp.com/unfi-insights"
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-[#EE6A4C] underline underline-offset-2"
        >
          UNFI Insights
        </a>{" "}
        and sign in with your myUNFI credentials.
      </>
    ),
    image: "/guides/unfi-upload/step-1.png",
  },
  {
    title: "Open the Year Over Year Sales report",
    description:
      "Go to the Analytics tab and select Year Over Year Sales under Business Health.",
    image: "/guides/unfi-upload/step-2.png",
  },
  {
    title: "Select the month you want to export",
    description:
      'Under Period Start Date, change the first selection to "is in the month," then choose the month and year you want to pull. Be sure to click the reload button after changing the period so the report refreshes.',
    image: "/guides/unfi-upload/step-3.png",
  },
  {
    title: "Download the detailed sales table",
    description:
      "Scroll to the bottom of the report to Year Over Year Sales Details. Open the three-dot menu on the table and select Download data.",
    image: "/guides/unfi-upload/step-4.png",
  },
  {
    title: "Export all results as CSV",
    description:
      'Set the format to CSV, then under Number of rows to include select "All results." This is important so SKUba receives the complete report. Click Download when you are ready.',
    image: "/guides/unfi-upload/step-5.png",
  },
]

export default function DistributorDataUploadCard({
  distributor,
  apiBaseUrl,
  uploadMode = "standard",
  onUploadSuccess,
}: DistributorDataUploadCardProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const { org } = useOrg()

  const [files, setFiles] = useState<File[]>([])
  const [selectedMonth, setSelectedMonth] = useState("")
  const [isUploading, setIsUploading] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [errorMessage, setErrorMessage] = useState("")

  const [
    showUnfiTruncationWarning,
    setShowUnfiTruncationWarning,
  ] = useState(false)

  const [
    showExportInstructions,
    setShowExportInstructions,
  ] = useState(false)

  const [
    hasSeenExportInstructions,
    setHasSeenExportInstructions,
  ] = useState(false)

  const [guideStepIndex, setGuideStepIndex] = useState(0)

  const [monthPickerOpen, setMonthPickerOpen] =
    useState(false)

  const [pickerYear, setPickerYear] = useState(
    new Date().getFullYear()
  )

  const isKehe = distributor === "kehe"
  const isUnfi = distributor === "unfi"

  const distributorLabel = isKehe ? "KeHE" : "UNFI"

  const guideSteps = isKehe
    ? keheGuideSteps
    : unfiGuideSteps

  const activeGuideStep = guideSteps[guideStepIndex]
  const isFirstGuideStep = guideStepIndex === 0
  const isLastGuideStep =
    guideStepIndex === guideSteps.length - 1

  const openExportInstructions = () => {
    setGuideStepIndex(0)
    setShowExportInstructions(true)
  }

  const formattedSelectedMonth = selectedMonth
    ? new Date(
        `${selectedMonth}-01T00:00:00`
      ).toLocaleDateString("en-US", {
        month: "long",
        year: "numeric",
      })
    : "Select report month"

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const selectedFiles = Array.from(
      e.target.files ?? []
    )

    setFiles(selectedFiles)
    setSuccessMessage("")
    setErrorMessage("")
  }

  const handleMonthSelect = (monthIndex: number) => {
    const month = String(monthIndex + 1).padStart(
      2,
      "0"
    )

    const value = `${pickerYear}-${month}`

    setSelectedMonth(value)
    setMonthPickerOpen(false)
    setSuccessMessage("")
    setErrorMessage("")
  }

  const handleUpload = async (
    confirmAllResults = false
  ) => {
    if (!org?.id) {
      setErrorMessage("Organization not found.")
      return
    }

    if (files.length === 0) {
      setErrorMessage(
        "Please choose a CSV file to upload."
      )
      return
    }

    if (isUnfi && !selectedMonth) {
      setErrorMessage(
        "Please select the month this UNFI report covers."
      )
      return
    }

    setIsUploading(true)
    setSuccessMessage("")
    setErrorMessage("")

    try {
      const formData = new FormData()

      let url = ""

      // =====================================================
      // KeHE
      // =====================================================

      if (isKehe) {
        files.forEach((file) => {
          formData.append("files", file)
        })

        if (uploadMode === "free-trial") {
          formData.append("org_id", org.id)
          url = `${apiBaseUrl}/free-trial/upload/kehe`
        } else {
          url = `${apiBaseUrl}/upload/kehe?org_id=${encodeURIComponent(org.id)}`
        }
      }

      // =====================================================
      // UNFI
      // =====================================================
      
      if (isUnfi) {
        formData.append("file", files[0])
        formData.append("org_id", org.id)
        formData.append("month", selectedMonth)

        if (confirmAllResults) {
          formData.append(
            "confirm_all_results",
            "true"
          )
        }

        url =
          uploadMode === "free-trial"
            ? `${apiBaseUrl}/free-trial/upload/unfi`
            : `${apiBaseUrl}/upload/unfi`
      }

      const res = await fetch(url, {
        method: "POST",
        body: formData,
      })

      const data = await res
        .json()
        .catch(() => null)

      if (!res.ok) {
        if (
          res.status === 409 &&
          data?.detail?.code ===
            "unfi_possible_truncation"
        ) {
          setShowUnfiTruncationWarning(true)
          return
        }

        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : "Upload failed."
        )
      }

      setSuccessMessage(
        data?.message ||
          `${distributorLabel} report${
            files.length === 1 ? "" : "s"
          } uploaded successfully.`
      )

      setFiles([])

      if (isUnfi) {
        setSelectedMonth("")
      }

      if (inputRef.current) {
        inputRef.current.value = ""
      }

      onUploadSuccess?.()
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Something went wrong during upload."

      setErrorMessage(message)
    } finally {
      setIsUploading(false)
    }
  }

  const fileLabel =
    files.length === 0
      ? isKehe
        ? "Choose CSV files"
        : "Choose CSV file"
      : files.length === 1
        ? files[0].name
        : `${files.length} CSV files selected`

  const uploadDisabled =
    isUploading ||
    files.length === 0 ||
    (isUnfi && !selectedMonth)

  return (
    <>
      <div
        className="rounded-2xl border p-5 shadow-sm"
        style={{
          borderColor: theme.line,
          backgroundColor: "white",
        }}
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <p
              className="text-[12px] font-semibold uppercase tracking-[0.16em]"
              style={{ color: theme.muted }}
            >
              Data Upload
            </p>

            <h3
              className="text-lg font-semibold"
              style={{ color: theme.charcoal }}
            >
              Upload {distributorLabel} reports
            </h3>

            <p
              className="text-sm"
              style={{ color: theme.muted }}
            >
              {hasSeenExportInstructions
                ? isKehe
                  ? "Select one or more KeHE CSV reports and upload them together."
                  : "Select the month this UNFI report covers, then upload the CSV."
                : `Follow the ${distributorLabel} export steps before uploading your data.`}
            </p>
          </div>

          {/* =================================================
              FIRST-TIME CTA
          ================================================= */}

          {!hasSeenExportInstructions && (
            <button
              type="button"
              onClick={openExportInstructions}
              className="w-full rounded-xl px-6 py-3 text-sm font-semibold transition-opacity hover:opacity-90 md:w-auto"
              style={{
                backgroundColor: theme.coral,
                color: "white",
              }}
            >
              Upload {distributorLabel} data →
            </button>
          )}

          {/* =================================================
              UPLOAD CONTROLS
          ================================================= */}

          {hasSeenExportInstructions && (
            <div className="w-full md:w-auto">
              <div
                className={`
                  grid gap-3
                  ${
                    isUnfi
                      ? "sm:grid-cols-[190px_minmax(260px,1fr)_auto]"
                      : "sm:grid-cols-[minmax(300px,1fr)_auto]"
                  }
                `}
              >
                {/* UNFI month */}

                {isUnfi && (
                  <div className="min-w-0">
                    <p
                      className="mb-1.5 text-xs font-semibold"
                      style={{
                        color: theme.muted,
                      }}
                    >
                      Month
                    </p>

                    <div className="relative">
                      <button
                        type="button"
                        onClick={() =>
                          setMonthPickerOpen(
                            (open) => !open
                          )
                        }
                        className="flex h-[42px] w-full items-center justify-between rounded-xl border px-3 text-left text-sm"
                        style={{
                          borderColor: theme.line,
                          backgroundColor:
                            theme.surface,
                          color: selectedMonth
                            ? theme.charcoal
                            : theme.muted,
                        }}
                      >
                        <span className="truncate">
                          {formattedSelectedMonth}
                        </span>

                        <span
                          className="ml-2 text-sm"
                          style={{
                            color: theme.muted,
                          }}
                        >
                          ▾
                        </span>
                      </button>

                      {monthPickerOpen && (
                        <div
                          className="absolute left-0 top-[50px] z-50 w-[300px] rounded-2xl border bg-white p-4 shadow-xl"
                          style={{
                            borderColor:
                              theme.line,
                          }}
                        >
                          <div className="mb-4 flex items-center justify-between">
                            <button
                              type="button"
                              onClick={() =>
                                setPickerYear(
                                  (year) =>
                                    year - 1
                                )
                              }
                              className="flex h-8 w-8 items-center justify-center rounded-lg text-sm transition hover:bg-[#F8F4EC]"
                              style={{
                                color:
                                  theme.charcoal,
                              }}
                            >
                              ←
                            </button>

                            <span
                              className="text-sm font-semibold"
                              style={{
                                color:
                                  theme.charcoal,
                              }}
                            >
                              {pickerYear}
                            </span>

                            <button
                              type="button"
                              onClick={() =>
                                setPickerYear(
                                  (year) =>
                                    year + 1
                                )
                              }
                              className="flex h-8 w-8 items-center justify-center rounded-lg text-sm transition hover:bg-[#F8F4EC]"
                              style={{
                                color:
                                  theme.charcoal,
                              }}
                            >
                              →
                            </button>
                          </div>

                          <div className="grid grid-cols-3 gap-2">
                            {monthNames.map(
                              (month, index) => {
                                const value = `${pickerYear}-${String(
                                  index + 1
                                ).padStart(
                                  2,
                                  "0"
                                )}`

                                const selected =
                                  selectedMonth ===
                                  value

                                return (
                                  <button
                                    key={month}
                                    type="button"
                                    onClick={() =>
                                      handleMonthSelect(
                                        index
                                      )
                                    }
                                    className="rounded-xl px-3 py-2.5 text-sm font-medium transition"
                                    style={{
                                      backgroundColor:
                                        selected
                                          ? theme.coral
                                          : theme.surface,
                                      color: selected
                                        ? "white"
                                        : theme.charcoal,
                                    }}
                                  >
                                    {month}
                                  </button>
                                )
                              }
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* File */}

                <div className="min-w-0">
                  {isUnfi && (
                    <p
                      className="mb-1.5 text-xs font-semibold"
                      style={{
                        color: theme.muted,
                      }}
                    >
                      CSV report
                    </p>
                  )}

                  <label
                    className="flex h-[42px] cursor-pointer items-center rounded-xl border px-3 text-sm"
                    style={{
                      borderColor: theme.line,
                      backgroundColor:
                        theme.surface,
                      color:
                        files.length > 0
                          ? theme.charcoal
                          : theme.muted,
                    }}
                  >
                    <input
                      ref={inputRef}
                      type="file"
                      accept=".csv"
                      multiple={isKehe}
                      className="hidden"
                      onChange={
                        handleFileChange
                      }
                    />

                    <span className="truncate">
                      {fileLabel}
                    </span>
                  </label>
                </div>

                {/* Upload */}

                <div
                  className={
                    isUnfi
                      ? "sm:pt-[25px]"
                      : ""
                  }
                >
                  <button
                    type="button"
                    onClick={() =>
                      handleUpload()
                    }
                    disabled={uploadDisabled}
                    className="h-[42px] w-full rounded-xl px-5 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                    style={{
                      backgroundColor:
                        theme.blue,
                      color:
                        theme.charcoal,
                    }}
                  >
                    {isUploading
                      ? "Uploading..."
                      : "Upload"}
                  </button>
                </div>
              </div>

              {/* Instructions remain accessible */}

              <button
                type="button"
                onClick={openExportInstructions}
                className="mt-3 text-xs font-medium underline underline-offset-2"
                style={{
                  color: theme.muted,
                }}
              >
                View {distributorLabel} export
                instructions
              </button>

              {isKehe &&
                files.length > 1 && (
                  <div
                    className="mt-3 rounded-xl border px-3 py-2 text-xs"
                    style={{
                      borderColor:
                        theme.line,
                      backgroundColor:
                        theme.surface,
                      color:
                        theme.muted,
                    }}
                  >
                    {files.map((file) => (
                      <div
                        key={`${file.name}-${file.size}`}
                      >
                        {file.name}
                      </div>
                    ))}
                  </div>
                )}

              {successMessage && (
                <div
                  className="mt-3 rounded-xl px-3 py-2 text-sm font-medium"
                  style={{
                    backgroundColor:
                      theme.greenBg,
                    color:
                      theme.greenText,
                  }}
                >
                  {successMessage}
                </div>
              )}

              {errorMessage && (
                <div
                  className="mt-3 rounded-xl px-3 py-2 text-sm font-medium"
                  style={{
                    backgroundColor:
                      theme.redBg,
                    color: theme.redText,
                  }}
                >
                  {errorMessage}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* =====================================================
          EXPORT INSTRUCTIONS MODAL — ONE STEP AT A TIME
      ===================================================== */}

      {showExportInstructions && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 px-4 py-8">
          <div
            className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-[28px] border shadow-xl"
            style={{
              backgroundColor: "white",
              borderColor: theme.line,
            }}
          >
            {/* Header */}

            <div
              className="flex items-start justify-between border-b px-6 py-5"
              style={{
                borderColor: theme.line,
              }}
            >
              <div>
                <p
                  className="text-[12px] font-semibold uppercase tracking-[0.16em]"
                  style={{
                    color: theme.coral,
                  }}
                >
                  {distributorLabel} export guide
                </p>

                <h2
                  className="mt-1 text-2xl font-semibold"
                  style={{
                    color: theme.charcoal,
                  }}
                >
                  Export your {distributorLabel} data
                </h2>
              </div>

              {hasSeenExportInstructions && (
                <button
                  type="button"
                  onClick={() =>
                    setShowExportInstructions(
                      false
                    )
                  }
                  className="flex h-9 w-9 items-center justify-center rounded-full text-xl"
                  style={{
                    color: theme.muted,
                    backgroundColor:
                      theme.surface,
                  }}
                >
                  ×
                </button>
              )}
            </div>

            {/* Current step */}

            <div className="overflow-y-auto px-6 py-5">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p
                  className="text-xs font-semibold uppercase tracking-[0.14em]"
                  style={{
                    color: theme.muted,
                  }}
                >
                  Step {guideStepIndex + 1} of{" "}
                  {guideSteps.length}
                </p>

                <div className="flex gap-1.5">
                  {guideSteps.map((_, index) => (
                    <div
                      key={index}
                      className="h-1.5 w-8 rounded-full"
                      style={{
                        backgroundColor:
                          index <= guideStepIndex
                            ? theme.coral
                            : theme.line,
                      }}
                    />
                  ))}
                </div>
              </div>

              <h3
                className="text-xl font-semibold"
                style={{
                  color: theme.charcoal,
                }}
              >
                {activeGuideStep.title}
              </h3>

              <div
                className="mt-2 text-sm leading-relaxed"
                style={{
                  color: theme.muted,
                }}
              >
                {activeGuideStep.description}
              </div>

              <div
                className="mt-5 overflow-hidden rounded-2xl border"
                style={{
                  borderColor: theme.line,
                  backgroundColor:
                    theme.surface,
                }}
              >
                <div className="mt-5 flex justify-center">
                  <div
                    className="w-fit max-w-full overflow-hidden rounded-2xl border"
                    style={{
                      borderColor: theme.line,
                      backgroundColor: "white",
                    }}
                  >
                    <img
                      src={activeGuideStep.image}
                      alt={`${distributorLabel} export step ${
                        guideStepIndex + 1
                      }: ${activeGuideStep.title}`}
                      className="block h-auto max-h-[46vh] max-w-full object-contain"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Navigation */}

            <div
              className="flex items-center justify-between gap-3 border-t px-6 py-4"
              style={{
                borderColor: theme.line,
                backgroundColor:
                  theme.surface,
              }}
            >
              <button
                type="button"
                onClick={() =>
                  setGuideStepIndex(
                    (index) =>
                      Math.max(0, index - 1)
                  )
                }
                disabled={isFirstGuideStep}
                className="rounded-xl border px-5 py-3 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-35"
                style={{
                  borderColor: theme.line,
                  color: theme.charcoal,
                  backgroundColor: "white",
                }}
              >
                ← Back
              </button>

              {!isLastGuideStep ? (
                <button
                  type="button"
                  onClick={() =>
                    setGuideStepIndex(
                      (index) =>
                        Math.min(
                          guideSteps.length - 1,
                          index + 1
                        )
                    )
                  }
                  className="rounded-xl px-6 py-3 text-sm font-semibold"
                  style={{
                    backgroundColor:
                      theme.coral,
                    color: "white",
                  }}
                >
                  Next →
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setHasSeenExportInstructions(
                      true
                    )
                    setShowExportInstructions(
                      false
                    )
                  }}
                  className="rounded-xl px-6 py-3 text-sm font-semibold"
                  style={{
                    backgroundColor:
                      theme.coral,
                    color: "white",
                  }}
                >
                  {hasSeenExportInstructions
                    ? "Back to upload →"
                    : "Got it — let's upload →"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =====================================================
          UNFI 500-ROW WARNING
      ===================================================== */}

      {showUnfiTruncationWarning && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/30 px-4">
          <div
            className="w-full max-w-md rounded-[24px] border p-6 shadow-xl"
            style={{
              backgroundColor: "white",
              borderColor: theme.line,
            }}
          >
            <p
              className="text-[12px] font-semibold uppercase tracking-[0.14em]"
              style={{
                color: theme.redText,
              }}
            >
              Check your UNFI export
            </p>

            <h3
              className="mt-2 text-xl font-semibold"
              style={{
                color: theme.charcoal,
              }}
            >
              This file may be incomplete.
            </h3>

            <p
              className="mt-3 text-sm leading-relaxed"
              style={{
                color: theme.brown,
              }}
            >
              We detected exactly 500 rows of
              UNFI data. This can happen when
              the export is limited instead of
              including the full report.
            </p>

            <p
              className="mt-3 text-sm font-medium"
              style={{
                color: theme.charcoal,
              }}
            >
              When downloading from the UNFI
              Insights portal, did you select{" "}
              <strong>All results</strong> in the
              Download settings?
            </p>

            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={() => {
                  setShowUnfiTruncationWarning(
                    false
                  )
                }}
                className="flex-1 rounded-xl border px-4 py-3 text-sm font-medium"
                style={{
                  borderColor: theme.line,
                  color:
                    theme.charcoal,
                  backgroundColor:
                    theme.surface,
                }}
              >
                Go back and re-export
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowUnfiTruncationWarning(
                    false
                  )
                  handleUpload(true)
                }}
                className="flex-1 rounded-xl px-4 py-3 text-sm font-medium"
                style={{
                  backgroundColor:
                    theme.coral,
                  color: "white",
                }}
              >
                Yes, I selected All results
              </button>
            </div>

            <button
              type="button"
              onClick={() => {
                setShowUnfiTruncationWarning(
                  false
                )
                openExportInstructions()
              }}
              className="mt-4 w-full text-center text-xs italic underline underline-offset-2"
              style={{
                color: theme.muted,
              }}
            >
              View the full UNFI export steps to
              double-check.
            </button>
          </div>
        </div>
      )}
    </>
  )
}