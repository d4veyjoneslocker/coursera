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
  const org = useOrg() // 🔥 get org here

  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [errorMessage, setErrorMessage] = useState("")

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] ?? null
    setFile(selectedFile)
    setSuccessMessage("")
    setErrorMessage("")
  }

  const handleUpload = async () => {
    if (!file) {
      setErrorMessage("Please choose a CSV file to upload.")
      return
    }

    setIsUploading(true)
    setSuccessMessage("")
    setErrorMessage("")

    try {
      const formData = new FormData()
      formData.append("file", file)

      const res = await fetch(
        `${apiBaseUrl}/upload/kehe?org_id=${org.id}`, // 🔥 fixed
        {
          method: "POST",
          body: formData,
        }
      )

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed.")
      }

      setSuccessMessage(data.message || "Data uploaded successfully.")
      setFile(null)

      if (inputRef.current) {
        inputRef.current.value = ""
      }

      onUploadSuccess?.()
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong during upload."
      setErrorMessage(message)
    } finally {
      setIsUploading(false)
    }
  }

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
            Upload KeHE report
          </h3>

          <p
            className="text-sm"
            style={{ color: theme.muted }}
          >
            Upload your latest KeHE CSV to refresh dashboard data.
          </p>
        </div>

        <div className="flex w-full flex-col gap-3 md:w-auto md:min-w-[420px]">
          <div className="flex flex-col gap-3 sm:flex-row">
            <label
              className="flex min-h-[42px] flex-1 cursor-pointer items-center rounded-xl border px-3 py-2 text-sm"
              style={{
                borderColor: theme.line,
                backgroundColor: theme.surface,
                color: file ? theme.charcoal : theme.muted,
              }}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileChange}
              />
              <span className="truncate">
                {file ? file.name : "Choose CSV file"}
              </span>
            </label>

            <button
              type="button"
              onClick={handleUpload}
              disabled={isUploading || !file}
              className="rounded-xl px-4 py-2 text-sm font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                backgroundColor: theme.blue,
                color: theme.charcoal,
              }}
            >
              {isUploading ? "Uploading..." : "Upload"}
            </button>
          </div>

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