"use client"

import { useRef, useState } from "react"
import { useOrg } from "@/components/OrgContext"

type KeheUploadCardProps = {
  apiBaseUrl: string
  onUploadSuccess?: () => void
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
}

export default function KeheUploadCard({
  apiBaseUrl,
  onUploadSuccess,
}: KeheUploadCardProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const { org } = useOrg()

  const [files, setFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [errorMessage, setErrorMessage] = useState("")

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files ?? [])

    setFiles(selectedFiles)
    setSuccessMessage("")
    setErrorMessage("")
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      setErrorMessage("Please choose at least one CSV file to upload.")
      return
    }

    setIsUploading(true)
    setSuccessMessage("")
    setErrorMessage("")

    try {
      const formData = new FormData()

      files.forEach((file) => {
        formData.append("files", file)
      })

      const res = await fetch(
        `${apiBaseUrl}/upload/kehe?org_id=${org.id}`,
        {
          method: "POST",
          body: formData,
        }
      )

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed.")
      }

      setSuccessMessage(
        data.message || `${files.length} file${files.length === 1 ? "" : "s"} uploaded successfully.`
      )

      setFiles([])

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
      ? "Choose CSV files"
      : files.length === 1
        ? files[0].name
        : `${files.length} CSV files selected`

  return (
    <div
      className="rounded-2xl border p-5 shadow-sm"
      style={{
        borderColor: theme.line,
        backgroundColor: "white",
      }}
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
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
            Upload KeHE reports
          </h3>

          <p
            className="text-sm"
            style={{ color: theme.muted }}
          >
            Select one or more KeHE CSV reports and upload them together.
          </p>
        </div>

        <div className="flex w-full flex-col gap-3 md:w-auto md:min-w-[420px]">
          <div className="flex flex-col gap-3 sm:flex-row">
            <label
              className="flex min-h-[42px] flex-1 cursor-pointer items-center rounded-xl border px-3 py-2 text-sm"
              style={{
                borderColor: theme.line,
                backgroundColor: theme.surface,
                color: files.length > 0 ? theme.charcoal : theme.muted,
              }}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".csv"
                multiple
                className="hidden"
                onChange={handleFileChange}
              />

              <span className="truncate">
                {fileLabel}
              </span>
            </label>

            <button
              type="button"
              onClick={handleUpload}
              disabled={isUploading || files.length === 0}
              className="rounded-xl px-4 py-2 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                backgroundColor: theme.blue,
                color: theme.charcoal,
              }}
            >
              {isUploading ? "Uploading..." : "Upload"}
            </button>
          </div>

          {files.length > 1 && (
            <div
              className="rounded-xl border px-3 py-2 text-xs"
              style={{
                borderColor: theme.line,
                backgroundColor: theme.surface,
                color: theme.muted,
              }}
            >
              {files.map((file) => (
                <div key={`${file.name}-${file.size}`}>
                  {file.name}
                </div>
              ))}
            </div>
          )}

          {successMessage && (
            <div
              className="rounded-xl px-3 py-2 text-sm font-medium"
              style={{
                backgroundColor: theme.greenBg,
                color: theme.greenText,
              }}
            >
              {successMessage}
            </div>
          )}

          {errorMessage && (
            <div
              className="rounded-xl px-3 py-2 text-sm font-medium"
              style={{
                backgroundColor: theme.redBg,
                color: theme.redText,
              }}
            >
              {errorMessage}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}