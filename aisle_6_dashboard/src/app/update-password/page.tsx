"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"

export default function UpdatePasswordPage() {
  const router = useRouter()

  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState("")

  const theme = {
    bg: "#F7F3E8",
    surface: "#FFFDF8",
    gold: "#F7B045",
    brown: "#705C4F",
    charcoal: "#343332",
    line: "#D8CFB7",
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setStatus("")

    const { error } = await supabase.auth.updateUser({
      password,
    })

    setLoading(false)

    if (error) {
      setStatus(
        error.message === "Auth session missing!"
          ? "This reset link has expired or is no longer valid. Please request a new password reset link."
          : error.message
      )
      return
    }

    setStatus("Password updated. Redirecting...")

    setTimeout(() => {
      router.push("/login")
    }, 1000)
  }

  return (
    <main
      className="flex min-h-screen items-center justify-center px-6 py-10"
      style={{ backgroundColor: theme.bg, color: theme.charcoal }}
    >
      <section
        className="w-full max-w-md rounded-[32px] border p-7 md:p-8"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.line,
          boxShadow: "0 18px 50px rgba(52,51,50,0.08)",
        }}
      >
        <div className="mb-8 space-y-3">
          <div className="flex items-center gap-3">
            <div
              className="h-[3px] w-12 rounded-full"
              style={{ backgroundColor: theme.gold }}
            />
            <p
              className="text-xs font-semibold uppercase tracking-[0.25em]"
              style={{ color: theme.brown }}
            >
              SKUba
            </p>
          </div>

          <h1 className="text-3xl font-semibold">Set a new password</h1>

          <p className="text-sm leading-6" style={{ color: theme.brown }}>
            Enter a new password for your account.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              New password
            </label>

            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Create a new password"
              autoComplete="new-password"
              className="w-full rounded-2xl border px-4 py-3 text-sm outline-none transition"
              style={{
                borderColor: theme.line,
                backgroundColor: "#FFFFFF",
                color: theme.charcoal,
              }}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-2xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-70"
            style={{
              backgroundColor: theme.charcoal,
              color: "#FFFFFF",
            }}
          >
            {loading ? "Updating password..." : "Update password"}
          </button>
        </form>

        {status && (
          <div
            className="mt-5 rounded-2xl border px-4 py-3 text-sm"
            style={{
              borderColor: theme.line,
              backgroundColor: theme.bg,
              color: theme.brown,
            }}
          >
            {status}
          </div>
        )}

        {/* helpful fallback */}
        <div className="mt-6 text-xs leading-6" style={{ color: theme.brown }}>
          Need a new link?{" "}
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="font-semibold underline underline-offset-4"
          >
            Go back to login
          </button>
        </div>
      </section>
    </main>
  )
}