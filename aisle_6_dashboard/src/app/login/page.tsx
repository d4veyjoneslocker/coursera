"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { supabase } from "@/lib/supabase"

export default function LoginPage() {
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
    surface: "#EFE7D2",
    blue: "#92B9DC",
    gold: "#F7B045",
    brown: "#705C4F",
    charcoal: "#343332",
    line: "#D8CFB7",
  }

  useEffect(() => {
    setMounted(true)

    const checkSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (session?.user) {
        router.push("/")
      }
    }

    checkSession()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        router.push("/")
      }
    })

    return () => subscription.unsubscribe()
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setStatus("")

    try {
      if (mode === "signup") {
        if (!orgName.trim()) {
          setStatus("Please enter your brand name.")
          setLoading(false)
          return
        }

        const { data: signUpData, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        })

        if (signUpError) {
          setStatus(signUpError.message)
          setLoading(false)
          return
        }

        const user = signUpData.user

        if (!user) {
          setStatus("User was created, but no user record was returned.")
          setLoading(false)
          return
        }

        const { data: orgData, error: orgError } = await supabase
          .from("organizations")
          .insert({
            name: orgName.trim(),
          })
          .select("id")
          .single()

        if (orgError) {
          setStatus(`Organization error: ${orgError.message}`)
          setLoading(false)
          return
        }

        const { error: profileError } = await supabase
          .from("profiles")
          .insert({
            user_id: user.id,
            org_id: orgData.id,
          })

        if (profileError) {
          setStatus(`Profile error: ${profileError.message}`)
          setLoading(false)
          return
        }

        setStatus("Account created successfully. You can log in now.")
        setMode("login")
        setOrgName("")
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })

        if (error) {
          setStatus(error.message)
        } else {
          setStatus("Logged in. Redirecting...")
        }
      }
    } catch {
      setStatus("Something went wrong. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  if (!mounted) return null

  return (
    <main
      className="min-h-screen px-6 py-10 md:px-10"
      style={{ backgroundColor: theme.bg, color: theme.charcoal }}
    >
      <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-[1.05fr_0.95fr]">
        <section
          className="relative overflow-hidden rounded-[32px] border p-8 md:p-10"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <div
            className="absolute right-0 top-0 h-40 w-40 translate-x-10 -translate-y-10 rounded-full blur-2xl"
            style={{ backgroundColor: theme.blue + "55" }}
          />
          <div
            className="absolute bottom-0 left-0 h-40 w-40 -translate-x-10 translate-y-10 rounded-full blur-2xl"
            style={{ backgroundColor: theme.gold + "33" }}
          />

          <div className="relative z-10 space-y-8">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div
                  className="h-[3px] w-14 rounded-full"
                  style={{ backgroundColor: theme.gold }}
                />
                <p
                  className="text-xs font-semibold uppercase tracking-[0.25em]"
                  style={{ color: theme.brown }}
                >
                  SKUba
                </p>
              </div>

              <div className="space-y-3">
                <h1 className="max-w-xl text-4xl font-semibold leading-tight md:text-5xl">
                  Your retail data,
                  <br />
                  finally in one place.
                </h1>
                <p
                  className="max-w-lg text-base leading-7 md:text-lg"
                  style={{ color: theme.brown }}
                >
                  Clean sales reporting, better visibility, and a faster way to
                  understand what is actually happening across accounts, SKUs,
                  and distributors.
                </p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <FeatureCard
                title="Clean inputs"
                body="Standardized data that is actually usable."
                accent={theme.blue}
                theme={theme}
              />
              <FeatureCard
                title="Clear trends"
                body="See what is moving without digging through exports."
                accent={theme.gold}
                theme={theme}
              />
              <FeatureCard
                title="Built for brands"
                body="A workflow that feels more like a CPG tool than a BI app."
                accent={theme.brown}
                theme={theme}
              />
            </div>
          </div>
        </section>

        <section
          className="rounded-[32px] border p-7 md:p-8"
          style={{
            backgroundColor: "#FFFDF8",
            borderColor: theme.line,
            boxShadow: "0 10px 30px rgba(52,51,50,0.04)",
          }}
        >
          <div className="space-y-6">
            <div className="space-y-2">
              <p
                className="text-xs font-semibold uppercase tracking-[0.22em]"
                style={{ color: theme.brown }}
              >
                Welcome
              </p>
              <h2 className="text-3xl font-semibold">
                {mode === "login" ? "Log in to SKUba" : "Create your account"}
              </h2>
              <p className="text-sm leading-6" style={{ color: theme.brown }}>
                {mode === "login"
                  ? "Use your email and password to access your dashboard."
                  : "Start with a simple account setup for your brand."}
              </p>
            </div>

            <div
              className="inline-flex rounded-2xl border p-1"
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
                  backgroundColor:
                    mode === "login" ? theme.charcoal : "transparent",
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

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "signup" && (
                <div className="space-y-2">
                  <label
                    htmlFor="orgName"
                    className="text-sm font-medium"
                    style={{ color: theme.charcoal }}
                  >
                    Brand name
                  </label>
                  <input
                    id="orgName"
                    type="text"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="SKUba"
                    className="w-full rounded-2xl border px-4 py-3 text-sm outline-none transition"
                    style={{
                      borderColor: theme.line,
                      backgroundColor: "#FFFFFF",
                      color: theme.charcoal,
                    }}
                    required={mode === "signup"}
                  />
                </div>
              )}

              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium"
                  style={{ color: theme.charcoal }}
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@brand.com"
                  className="w-full rounded-2xl border px-4 py-3 text-sm outline-none transition"
                  style={{
                    borderColor: theme.line,
                    backgroundColor: "#FFFFFF",
                    color: theme.charcoal,
                  }}
                  required
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="password"
                  className="text-sm font-medium"
                  style={{ color: theme.charcoal }}
                >
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={
                    mode === "login"
                      ? "Enter your password"
                      : "Create a password"
                  }
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
                {loading
                  ? mode === "login"
                    ? "Logging in..."
                    : "Creating account..."
                  : mode === "login"
                    ? "Log in"
                    : "Create account"}
              </button>
            </form>

            <div
              className="min-h-[52px] rounded-2xl border px-4 py-3 text-sm"
              style={{
                borderColor: status ? theme.line : "transparent",
                backgroundColor: status ? theme.bg : "transparent",
                color: theme.brown,
              }}
            >
              {status || " "}
            </div>

            <p className="text-xs leading-6" style={{ color: theme.brown }}>
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
          </div>
        </section>
      </div>
    </main>
  )
}

function FeatureCard({
  title,
  body,
  accent,
  theme,
}: {
  title: string
  body: string
  accent: string
  theme: {
    surface: string
    line: string
    brown: string
  }
}) {
  return (
    <div
      className="rounded-[24px] border p-4"
      style={{
        backgroundColor: "#FFFDF8",
        borderColor: theme.line,
      }}
    >
      <div
        className="mb-3 h-[3px] w-10 rounded-full"
        style={{ backgroundColor: accent }}
      />
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-6" style={{ color: theme.brown }}>
        {body}
      </p>
    </div>
  )
}