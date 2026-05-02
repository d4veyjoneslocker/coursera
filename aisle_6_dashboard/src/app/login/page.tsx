"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"

export default function LoginPage() {

  console.log("LOGIN PAGE RENDERED")

  const router = useRouter()

  const [mode, setMode] = useState<"login" | "signup">("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [orgName, setOrgName] = useState("")
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState("")
  const [mounted, setMounted] = useState(false)

  const theme = {
    bg: "#F7F3E8",
    surface: "#FFFDF8",
    gold: "#F7B045",
    brown: "#705C4F",
    charcoal: "#343332",
    line: "#D8CFB7",
  }

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setStatus("")

    try {
      if (mode === "signup") {
        const trimmedOrgName = orgName.trim()

        if (!trimmedOrgName) {
          setStatus("Please enter your brand name.")
          return
        }

        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        })

        if (signUpError) {
          setStatus(signUpError.message)
          return
        }

        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        })

        if (signInError) {
          setStatus(`Signup worked, but login failed: ${signInError.message}`)
          return
        }

        const {
          data: { session },
        } = await supabase.auth.getSession()

        if (!session?.user) {
          setStatus("Signup worked, but no active session was created.")
          return
        }

        const user = session.user

        if (!user) {
          setStatus("Account created, but no user record was returned.")
          return
        }

        const { error: rpcError } = await supabase.rpc("create_org_and_profile", {
          org_name: trimmedOrgName,
        })

        if (rpcError) {
          setStatus(`Setup error: ${rpcError.message}`)
          return
        }



        setStatus("Account created. Redirecting...")
        router.push("/")
        return
      }

      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      console.log("LOGIN DATA:", data)
      console.log("LOGIN ERROR:", error)

      if (error) {
        setStatus(error.message)
        return
      }

      const {
        data: { session },
      } = await supabase.auth.getSession()

      console.log("SESSION AFTER LOGIN:", session)

      setStatus("Logged in. Redirecting...")

      setTimeout(() => {
        window.location.assign(window.location.origin + "/")
      }, 1000)

    } catch (err) {
      console.error(err)
      setStatus("Something went wrong. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  if (!mounted) return null

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

          <h1 className="text-3xl font-semibold">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h1>

          <p className="text-sm leading-6" style={{ color: theme.brown }}>
            {mode === "login"
              ? "Log in to access your dashboard."
              : "Set up your brand account and start building your dashboard."}
          </p>
        </div>

        <div
          className="mb-6 inline-flex rounded-2xl border p-1"
          style={{
            borderColor: theme.line,
            backgroundColor: theme.bg,
          }}
        >
          <button
            type="button"
            onClick={() => {
              setMode("login")
              setStatus("")
            }}
            className="rounded-xl px-4 py-2 text-sm font-medium transition"
            style={{
              backgroundColor: mode === "login" ? theme.charcoal : "transparent",
              color: mode === "login" ? "#FFFFFF" : theme.brown,
            }}
          >
            Log in
          </button>

          <button
            type="button"
            onClick={() => {
              setMode("signup")
              setStatus("")
            }}
            className="rounded-xl px-4 py-2 text-sm font-medium transition"
            style={{
              backgroundColor:
                mode === "signup" ? theme.charcoal : "transparent",
              color: mode === "signup" ? "#FFFFFF" : theme.brown,
            }}
          >
            Sign up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {mode === "signup" && (
            <AuthInput
              id="orgName"
              label="Brand name"
              type="text"
              value={orgName}
              onChange={setOrgName}
              placeholder="Your brand"
              theme={theme}
            />
          )}

          <AuthInput
            id="email"
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="you@brand.com"
            autoComplete="email"
            theme={theme}
          />

          <AuthInput
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder={
              mode === "login" ? "Enter your password" : "Create a password"
            }
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            theme={theme}
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-2xl px-4 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-70"
            style={{
              backgroundColor: theme.charcoal,
              color: "#FFFFFF",
            }}
          >
            {loading
              ? mode === "login"
                ? "Logging in..."
                : "Creating account..."
              : mode === "login"
                ? "Log in"
                : "Create account"}
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

        <p className="mt-6 text-xs leading-6" style={{ color: theme.brown }}>
          {mode === "login" ? (
            <>
              Need an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("signup")
                  setStatus("")
                }}
                className="font-semibold underline underline-offset-4"
              >
                Create one
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setMode("login")
                  setStatus("")
                }}
                className="font-semibold underline underline-offset-4"
              >
                Log in
              </button>
            </>
          )}
        </p>
      </section>
    </main>
  )
}

function AuthInput({
  id,
  label,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
  theme,
}: {
  id: string
  label: string
  type: string
  value: string
  onChange: (value: string) => void
  placeholder: string
  autoComplete?: string
  theme: {
    line: string
    charcoal: string
  }
}) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className="w-full rounded-2xl border px-4 py-3 text-sm outline-none transition"
        style={{
          borderColor: theme.line,
          backgroundColor: "#FFFFFF",
          color: theme.charcoal,
        }}
        required
      />
    </div>
  )
}