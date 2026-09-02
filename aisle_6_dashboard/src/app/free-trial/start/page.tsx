"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowRight, Check } from "lucide-react"
import { supabase } from "@/lib/supabase"

type Distributor = "kehe" | "unfi" | "other"

type StartDate = {
  month: string
  year: string
}

type Step = "welcome" | "business" | "activate"

type OrgDistributorInsert = {
  org_id: string
  distributor: string
  start_date: string | null
  is_supported: boolean
}

const theme = {
  background: "#F6F2EA",
  surface: "#FCFAF6",
  card: "#FFFEFB",
  line: "#EEE5D8",
  brown: "#705C4F",
  charcoal: "#343332",
  muted: "#9A8A7C",
}

const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]

const currentYear = new Date().getFullYear()

const years = Array.from(
  { length: 15 },
  (_, index) => String(currentYear - index)
)

function startDateToIso(startDate: StartDate): string | null {
  if (!startDate.month || !startDate.year) {
    return null
  }

  const monthIndex = months.indexOf(startDate.month)

  if (monthIndex === -1) {
    return null
  }

  const monthNumber = String(monthIndex + 1).padStart(2, "0")

  return `${startDate.year}-${monthNumber}-01`
}

function parseOtherDistributors(value: string): string[] {
  return value
    .split(",")
    .map((distributor) => distributor.trim())
    .filter(Boolean)
}

export default function FreeTrialStartPage() {
  const router = useRouter()

  /*
   * FLOW
   */

  const [step, setStep] = useState<Step>("welcome")

  /*
   * BUSINESS INFO
   */

  const [brandName, setBrandName] = useState("")

  const [distributors, setDistributors] = useState<
    Distributor[]
  >([])

  const [otherDistributors, setOtherDistributors] =
    useState("")

  const [keheStart, setKeheStart] = useState<StartDate>({
    month: "",
    year: "",
  })

  const [unfiStart, setUnfiStart] = useState<StartDate>({
    month: "",
    year: "",
  })

  const [error, setError] = useState<string | null>(null)

  /*
   * ACTIVATION
   */

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  const [activationError, setActivationError] =
    useState<string | null>(null)

  const [isActivating, setIsActivating] =
    useState(false)

  /*
   * BUSINESS INFO HELPERS
   */

  function toggleDistributor(
    distributor: Distributor
  ) {
    setDistributors((current) => {
      if (current.includes(distributor)) {
        return current.filter(
          (item) => item !== distributor
        )
      }

      return [...current, distributor]
    })
  }

  function handleBusinessContinue() {
    setError(null)

    if (!brandName.trim()) {
      setError("Enter your brand name.")
      return
    }

    if (distributors.length === 0) {
      setError("Select at least one distributor.")
      return
    }

    /*
     * A free analysis currently requires at least
     * one supported distributor.
     */

    const hasSupportedDistributor =
      distributors.includes("kehe") ||
      distributors.includes("unfi")

    if (!hasSupportedDistributor) {
      setError(
        "The free analysis currently requires KeHE or UNFI data."
      )
      return
    }

    if (
      distributors.includes("kehe") &&
      (!keheStart.month || !keheStart.year)
    ) {
      setError(
        "Tell us when you started working with KeHE."
      )
      return
    }

    if (
      distributors.includes("unfi") &&
      (!unfiStart.month || !unfiStart.year)
    ) {
      setError(
        "Tell us when you started working with UNFI."
      )
      return
    }

    if (
      distributors.includes("other") &&
      !otherDistributors.trim()
    ) {
      setError(
        "Tell us which other distributors you work with."
      )
      return
    }

    setStep("activate")
  }

  /*
   * ACCOUNT CREATION
   */

  async function handleActivate() {
    setActivationError(null)

    const trimmedEmail = email.trim()
    const trimmedBrandName = brandName.trim()

    if (!trimmedEmail) {
      setActivationError("Enter your work email.")
      return
    }

    if (password.length < 8) {
      setActivationError(
        "Create a password with at least 8 characters."
      )
      return
    }

    if (!trimmedBrandName) {
      setActivationError("Enter your brand name.")
      return
    }

    setIsActivating(true)

    try {
      /*
       * 1. CREATE AUTH USER
       */

      const { error: signUpError } =
        await supabase.auth.signUp({
          email: trimmedEmail,
          password,
        })

      if (signUpError) {
        setActivationError(signUpError.message)
        return
      }

      /*
       * 2. SIGN USER IN
       *
       * This matches the existing signup flow
       * in your login page.
       */

      const { error: signInError } =
        await supabase.auth.signInWithPassword({
          email: trimmedEmail,
          password,
        })

      if (signInError) {
        setActivationError(
          `Signup worked, but login failed: ${signInError.message}`
        )
        return
      }

      /*
       * 3. CONFIRM SESSION
       */

      const {
        data: { session },
      } = await supabase.auth.getSession()

      if (!session?.user) {
        setActivationError(
          "Account created, but no active session was created."
        )
        return
      }

      const user = session.user

      /*
       * 4. CREATE ORG + PROFILE
       */

      const { error: rpcError } = await supabase.rpc(
        "create_org_and_profile",
        {
          org_name: trimmedBrandName,
        }
      )

      if (rpcError) {
        setActivationError(
          `Setup error: ${rpcError.message}`
        )
        return
      }

      /*
       * 5. GET NEW ORG ID
       *
       * create_org_and_profile currently doesn't
       * return the org id, so read it from the
       * profile that was just created.
       */

      const {
        data: profile,
        error: profileError,
      } = await supabase
        .from("profiles")
        .select("org_id")
        .eq("user_id", user.id)
        .single()

      if (profileError || !profile?.org_id) {
        console.error("PROFILE ERROR:", profileError)

        setActivationError(
          "Your account was created, but we couldn't finish setting up your organization."
        )
        return
      }

      const orgId = profile.org_id

      /*
       * 6. BUILD ORG DISTRIBUTOR ROWS
       */

      const distributorRows: OrgDistributorInsert[] =
        []

      if (distributors.includes("kehe")) {
        distributorRows.push({
          org_id: orgId,
          distributor: "kehe",
          start_date: startDateToIso(keheStart),
          is_supported: true,
        })
      }

      if (distributors.includes("unfi")) {
        distributorRows.push({
          org_id: orgId,
          distributor: "unfi",
          start_date: startDateToIso(unfiStart),
          is_supported: true,
        })
      }

      if (distributors.includes("other")) {
        const others =
          parseOtherDistributors(otherDistributors)

        for (const distributor of others) {
          distributorRows.push({
            org_id: orgId,

            /*
             * Keep user-entered distributor names
             * human-readable, but normalized.
             *
             * "Dot Foods" -> "dot foods"
             */
            distributor: distributor.toLowerCase(),

            /*
             * We aren't asking start dates for
             * unsupported distributors yet.
             */
            start_date: null,

            is_supported: false,
          })
        }
      }

      /*
       * 7. SAVE DISTRIBUTOR SETUP
       */

      if (distributorRows.length > 0) {
        const { error: distributorError } =
          await supabase
            .from("org_distributors")
            .insert(distributorRows)

        if (distributorError) {
          console.error(
            "ORG DISTRIBUTOR ERROR:",
            distributorError
          )

          setActivationError(
            "Your account was created, but we couldn't save your distributor setup."
          )
          return
        }
      }

      /*
       * 8. CONTINUE TO UPLOAD
       *
       * A full page navigation is intentional here.
       * It ensures the authenticated app layout /
       * OrgProvider initializes with the newly
       * created user and org.
       */

      window.location.assign(
        window.location.origin +
          "/free-trial/upload"
      )
    } catch (error) {
      console.error(error)

      setActivationError(
        "Something went wrong. Please try again."
      )
    } finally {
      setIsActivating(false)
    }
  }

  /*
   * WELCOME
   */

  if (step === "welcome") {
    return (
      <main
        className="min-h-screen px-6 py-8 md:px-10 md:py-10"
        style={{
          backgroundColor: theme.background,
        }}
      >
        <div className="mx-auto max-w-6xl">
          {/* HEADER */}

          <div className="flex items-center justify-between">
            <p
              className="text-[24px] font-semibold tracking-[-0.03em]"
              style={{
                color: theme.charcoal,
              }}
            >
              SKUba
            </p>

            <p
              className="hidden text-[12px] md:block"
              style={{
                color: theme.muted,
              }}
            >
              Built for emerging CPG brands
            </p>
          </div>

          {/* HERO */}

          <div className="grid min-h-[calc(100vh-120px)] items-center gap-14 py-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-20">
            {/* LEFT */}

            <div>
              <p
                className="text-[12px] font-medium uppercase tracking-[0.16em]"
                style={{
                  color: theme.brown,
                }}
              >
                Free distributor data analysis
              </p>

              <h1
                className="mt-5 max-w-[650px] text-[46px] font-semibold leading-[1.02] tracking-[-0.05em] md:text-[64px]"
                style={{
                  color: theme.charcoal,
                }}
              >
                Let&apos;s find what&apos;s hiding in
                your distributor data.
              </h1>

              <p
                className="mt-6 max-w-[570px] text-[17px] leading-[1.7]"
                style={{
                  color: theme.brown,
                }}
              >
                Upload your UNFI and KeHE data. SKUba
                will clean it, combine it, and surface
                the risks, opportunities, and changes
                worth your attention.
              </p>

              <div className="mt-9 flex flex-wrap items-center gap-5">
                <button
                  type="button"
                  onClick={() =>
                    setStep("business")
                  }
                  className="inline-flex items-center gap-2 rounded-lg px-6 py-3.5 text-[14px] font-medium transition-opacity hover:opacity-90"
                  style={{
                    backgroundColor:
                      theme.charcoal,
                    color: "#FFFFFF",
                  }}
                >
                  Start my free analysis
                  <ArrowRight size={16} />
                </button>

                <p
                  className="text-[12px]"
                  style={{
                    color: theme.muted,
                  }}
                >
                  No credit card required.
                </p>
              </div>
            </div>

            {/* RIGHT — TEMPORARY PREVIEW */}

            <div className="relative">
              <div
                className="border px-6 py-6 md:px-7 md:py-7"
                style={{
                  backgroundColor: theme.card,
                  borderColor: theme.line,
                }}
              >
                <div
                  className="flex items-start justify-between border-b pb-5"
                  style={{
                    borderColor: theme.line,
                  }}
                >
                  <div>
                    <p
                      className="text-[11px] font-medium uppercase tracking-[0.14em]"
                      style={{
                        color: theme.muted,
                      }}
                    >
                      What needs your attention
                    </p>

                    <p
                      className="mt-1 text-[18px] font-semibold"
                      style={{
                        color: theme.charcoal,
                      }}
                    >
                      SKUba found 8 things worth
                      reviewing.
                    </p>
                  </div>
                </div>

                {/* RISK */}

                <div
                  className="border-b py-6"
                  style={{
                    borderColor: theme.line,
                  }}
                >
                  <p
                    className="text-[11px] font-medium uppercase tracking-[0.12em]"
                    style={{
                      color: theme.brown,
                    }}
                  >
                    At risk
                  </p>

                  <p
                    className="mt-2 text-[16px] font-medium leading-[1.45]"
                    style={{
                      color: theme.charcoal,
                    }}
                  >
                    Sprouts has a higher concentration
                    of struggling stores than the rest
                    of the business.
                  </p>

                  <div className="mt-4 space-y-1.5">
                    <p
                      className="text-[13px]"
                      style={{
                        color: theme.brown,
                      }}
                    >
                      6 of 11 stores currently
                      struggling
                    </p>

                    <p
                      className="text-[13px]"
                      style={{
                        color: theme.brown,
                      }}
                    >
                      +45 pts vs. your overall average
                    </p>
                  </div>
                </div>

                {/* OPPORTUNITY */}

                <div className="py-6">
                  <p
                    className="text-[11px] font-medium uppercase tracking-[0.12em]"
                    style={{
                      color: theme.brown,
                    }}
                  >
                    Opportunity
                  </p>

                  <p
                    className="mt-2 text-[16px] font-medium leading-[1.45]"
                    style={{
                      color: theme.charcoal,
                    }}
                  >
                    Peanut Butter isn&apos;t sold in 63
                    ShopRite stores already buying
                    your brand.
                  </p>

                  <p
                    className="mt-4 text-[13px]"
                    style={{
                      color: theme.brown,
                    }}
                  >
                    ~2,464 annualized units of potential
                    upside
                  </p>
                </div>
              </div>

              {/* COMBINED DATA */}

              <div
                className="ml-auto mt-4 w-[78%] border px-5 py-4"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.line,
                }}
              >
                <p
                  className="text-[11px] font-medium uppercase tracking-[0.12em]"
                  style={{
                    color: theme.muted,
                  }}
                >
                  Your data, combined
                </p>

                <div className="mt-3 flex items-center gap-3">
                  <span
                    className="border px-3 py-1.5 text-[12px] font-medium"
                    style={{
                      borderColor: theme.line,
                      color: theme.charcoal,
                    }}
                  >
                    UNFI
                  </span>

                  <span
                    className="text-[13px]"
                    style={{
                      color: theme.muted,
                    }}
                  >
                    +
                  </span>

                  <span
                    className="border px-3 py-1.5 text-[12px] font-medium"
                    style={{
                      borderColor: theme.line,
                      color: theme.charcoal,
                    }}
                  >
                    KeHE
                  </span>

                  <ArrowRight
                    size={14}
                    style={{
                      color: theme.muted,
                    }}
                  />

                  <span
                    className="text-[12px] font-medium"
                    style={{
                      color: theme.brown,
                    }}
                  >
                    one analysis
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    )
  }

  /*
   * ACTIVATE
   */

  if (step === "activate") {
    return (
      <main
        className="min-h-screen px-6 py-14"
        style={{
          backgroundColor: theme.background,
        }}
      >
        <div className="mx-auto max-w-2xl">
          <div className="mb-8 text-center">
            <p
              className="text-[22px] font-semibold tracking-tight"
              style={{
                color: theme.charcoal,
              }}
            >
              SKUba
            </p>
          </div>

          <button
            type="button"
            onClick={() => setStep("business")}
            className="mb-5 text-[13px] font-medium"
            style={{
              color: theme.brown,
            }}
          >
            ← Back
          </button>

          <div
            className="rounded-[30px] border px-7 py-10 md:px-10 md:py-12"
            style={{
              backgroundColor: theme.card,
              borderColor: theme.line,
            }}
          >
            <p
              className="text-[12px] font-medium uppercase tracking-[0.16em]"
              style={{
                color: theme.muted,
              }}
            >
              Almost there
            </p>

            <h1
              className="mt-3 text-[34px] font-semibold leading-tight tracking-[-0.035em]"
              style={{
                color: theme.charcoal,
              }}
            >
              Activate your free analysis.
            </h1>

            <p
              className="mt-4 max-w-xl text-[15px] leading-[1.7]"
              style={{
                color: theme.brown,
              }}
            >
              Create a login so we can save your{" "}
              <span
                className="font-medium"
                style={{
                  color: theme.charcoal,
                }}
              >
                {brandName}
              </span>{" "}
              analysis and let you come back to your
              results.
            </p>

            <div className="mt-8 space-y-5">
              {/* EMAIL */}

              <div>
                <label
                  htmlFor="email"
                  className="mb-2 block text-[14px] font-medium"
                  style={{
                    color: theme.charcoal,
                  }}
                >
                  Work email
                </label>

                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(event.target.value)
                  }
                  placeholder="you@brand.com"
                  autoComplete="email"
                  className="w-full rounded-xl border bg-white px-4 py-3 text-[16px] outline-none transition focus:ring-2 focus:ring-black/5"
                  style={{
                    borderColor: theme.line,
                    color: theme.charcoal,
                  }}
                />
              </div>

              {/* PASSWORD */}

              <div>
                <label
                  htmlFor="password"
                  className="mb-2 block text-[14px] font-medium"
                  style={{
                    color: theme.charcoal,
                  }}
                >
                  Create password
                </label>

                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  placeholder="At least 8 characters"
                  autoComplete="new-password"
                  className="w-full rounded-xl border bg-white px-4 py-3 text-[16px] outline-none transition focus:ring-2 focus:ring-black/5"
                  style={{
                    borderColor: theme.line,
                    color: theme.charcoal,
                  }}
                />

                <p
                  className="mt-2 text-[12px]"
                  style={{
                    color: theme.muted,
                  }}
                >
                  Your account keeps your uploaded data
                  and analysis tied to your brand.
                </p>
              </div>

              {/* ERROR */}

              {activationError && (
                <div
                  className="rounded-xl border px-4 py-3 text-[13px]"
                  style={{
                    backgroundColor: "#FBF1EF",
                    borderColor: "#ECD8D3",
                    color: "#A06057",
                  }}
                >
                  {activationError}
                </div>
              )}

              {/* CTA */}

              <button
                type="button"
                onClick={handleActivate}
                disabled={isActivating}
                className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-[14px] font-medium transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
                style={{
                  backgroundColor:
                    theme.charcoal,
                  color: "#FFFFFF",
                }}
              >
                {isActivating
                  ? "Creating your analysis..."
                  : "Create account & continue"}

                {!isActivating && (
                  <ArrowRight size={16} />
                )}
              </button>

              <p
                className="text-center text-[12px] leading-relaxed"
                style={{
                  color: theme.muted,
                }}
              >
                No credit card required.
              </p>
            </div>
          </div>
        </div>
      </main>
    )
  }

  /*
   * BUSINESS INFO
   */

  return (
    <main
      className="min-h-screen px-6 py-14"
      style={{
        backgroundColor: theme.background,
      }}
    >
      <div className="mx-auto max-w-2xl">
        {/* LOGO */}

        <div className="mb-8 text-center">
          <p
            className="text-[22px] font-semibold tracking-tight"
            style={{
              color: theme.charcoal,
            }}
          >
            SKUba
          </p>
        </div>

        <button
          type="button"
          onClick={() => setStep("welcome")}
          className="mb-5 text-[13px] font-medium"
          style={{
            color: theme.brown,
          }}
        >
          ← Back
        </button>

        {/* FORM CARD */}

        <div
          className="rounded-[30px] border px-7 py-9 md:px-10 md:py-11"
          style={{
            backgroundColor: theme.card,
            borderColor: theme.line,
          }}
        >
          {/* INTRO */}

          <div className="mb-9">
            <p
              className="text-[12px] font-medium uppercase tracking-[0.16em]"
              style={{
                color: theme.muted,
              }}
            >
              First, a little context
            </p>

            <h1
              className="mt-3 text-[34px] font-semibold leading-tight tracking-[-0.035em] md:text-[38px]"
              style={{
                color: theme.charcoal,
              }}
            >
              Tell us about your business.
            </h1>

            <p
              className="mt-3 max-w-xl text-[15px] leading-[1.7]"
              style={{
                color: theme.brown,
              }}
            >
              This helps SKUba understand your
              distributor history and analyze your
              data correctly.
            </p>
          </div>

          <div className="space-y-8">
            {/* BRAND */}

            <div>
              <label
                htmlFor="brand-name"
                className="mb-2 block text-[14px] font-medium"
                style={{
                  color: theme.charcoal,
                }}
              >
                Brand name
              </label>

              <input
                id="brand-name"
                type="text"
                value={brandName}
                onChange={(event) =>
                  setBrandName(event.target.value)
                }
                placeholder="e.g. Goodles"
                className="w-full rounded-xl border bg-white px-4 py-3 text-[16px] outline-none transition focus:ring-2 focus:ring-black/5"
                style={{
                  borderColor: theme.line,
                  color: theme.charcoal,
                }}
              />
            </div>

            {/* DISTRIBUTORS */}

            <div>
              <p
                className="text-[14px] font-medium"
                style={{
                  color: theme.charcoal,
                }}
              >
                Which distributors do you work with?
              </p>

              <p
                className="mt-1 text-[13px]"
                style={{
                  color: theme.muted,
                }}
              >
                Select all that apply.
              </p>

              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <DistributorButton
                  label="KeHE"
                  selected={distributors.includes(
                    "kehe"
                  )}
                  onClick={() =>
                    toggleDistributor("kehe")
                  }
                />

                <DistributorButton
                  label="UNFI"
                  selected={distributors.includes(
                    "unfi"
                  )}
                  onClick={() =>
                    toggleDistributor("unfi")
                  }
                />

                <DistributorButton
                  label="Other"
                  selected={distributors.includes(
                    "other"
                  )}
                  onClick={() =>
                    toggleDistributor("other")
                  }
                />
              </div>

              {distributors.includes("other") && (
                <>
                  <div className="mt-4">
                    <label
                      htmlFor="other-distributors"
                      className="mb-2 block text-[13px] font-medium"
                      style={{
                        color: theme.charcoal,
                      }}
                    >
                      Which other distributors?
                    </label>

                    <input
                      id="other-distributors"
                      type="text"
                      value={otherDistributors}
                      onChange={(event) =>
                        setOtherDistributors(
                          event.target.value
                        )
                      }
                      placeholder="e.g. Dot Foods, McLane"
                      className="w-full rounded-xl border bg-white px-4 py-3 text-[16px] outline-none"
                      style={{
                        borderColor: theme.line,
                        color: theme.charcoal,
                      }}
                    />
                  </div>

                  <div
                    className="mt-4 rounded-xl border px-4 py-3"
                    style={{
                      backgroundColor:
                        theme.surface,
                      borderColor: theme.line,
                    }}
                  >
                    <p
                      className="text-[13px] leading-[1.65]"
                      style={{
                        color: theme.brown,
                      }}
                    >
                      For now, your free analysis will
                      include UNFI and KeHE. If you
                      subscribe, the SKUba team can add
                      your other distributors wherever
                      sufficient data is available.
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* KEHE DATE */}

            {distributors.includes("kehe") && (
              <DistributorStartDate
                distributor="KeHE"
                value={keheStart}
                onChange={setKeheStart}
              />
            )}

            {/* UNFI DATE */}

            {distributors.includes("unfi") && (
              <DistributorStartDate
                distributor="UNFI"
                value={unfiStart}
                onChange={setUnfiStart}
              />
            )}

            {/* ERROR */}

            {error && (
              <div
                className="rounded-xl border px-4 py-3 text-[13px]"
                style={{
                  backgroundColor: "#FBF1EF",
                  borderColor: "#ECD8D3",
                  color: "#A06057",
                }}
              >
                {error}
              </div>
            )}

            {/* CONTINUE */}

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={handleBusinessContinue}
                className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-[14px] font-medium transition-opacity hover:opacity-90"
                style={{
                  backgroundColor:
                    theme.charcoal,
                  color: "#FFFFFF",
                }}
              >
                Continue
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

function DistributorButton({
  label,
  selected,
  onClick,
}: {
  label: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-[52px] items-center justify-between rounded-xl border px-4 text-left text-[15px] font-medium transition"
      style={{
        backgroundColor: selected
          ? theme.surface
          : "#FFFFFF",
        borderColor: selected
          ? theme.brown
          : theme.line,
        color: theme.charcoal,
      }}
    >
      {label}

      <span
        className="flex h-5 w-5 items-center justify-center rounded-full border"
        style={{
          backgroundColor: selected
            ? theme.brown
            : "#FFFFFF",
          borderColor: selected
            ? theme.brown
            : theme.line,
          color: "#FFFFFF",
        }}
      >
        {selected && (
          <Check
            size={12}
            strokeWidth={3}
          />
        )}
      </span>
    </button>
  )
}

function DistributorStartDate({
  distributor,
  value,
  onChange,
}: {
  distributor: string
  value: StartDate
  onChange: (value: StartDate) => void
}) {
  return (
    <div>
      <p
        className="text-[14px] font-medium"
        style={{
          color: theme.charcoal,
        }}
      >
        When did you start working with{" "}
        {distributor}?
      </p>

      <p
        className="mt-1 text-[13px] leading-relaxed"
        style={{
          color: theme.muted,
        }}
      >
        This helps us understand whether your
        uploaded data represents your full
        distributor history.
      </p>

      <div className="mt-3 grid grid-cols-2 gap-3">
        <select
          value={value.month}
          onChange={(event) =>
            onChange({
              ...value,
              month: event.target.value,
            })
          }
          className="w-full rounded-xl border bg-white px-4 py-3 text-[16px] outline-none"
          style={{
            borderColor: theme.line,
            color: value.month
              ? theme.charcoal
              : theme.muted,
          }}
        >
          <option value="">
            Month
          </option>

          {months.map((month) => (
            <option
              key={month}
              value={month}
            >
              {month}
            </option>
          ))}
        </select>

        <select
          value={value.year}
          onChange={(event) =>
            onChange({
              ...value,
              year: event.target.value,
            })
          }
          className="w-full rounded-xl border bg-white px-4 py-3 text-[16px] outline-none"
          style={{
            borderColor: theme.line,
            color: value.year
              ? theme.charcoal
              : theme.muted,
          }}
        >
          <option value="">
            Year
          </option>

          {years.map((year) => (
            <option
              key={year}
              value={year}
            >
              {year}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}