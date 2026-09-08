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

type LeadModalType =
  | "short_history"
  | "other_distributor"
  | null

type SubmissionOutcome =
  | "short_history"
  | "other_only"
  | "proceeded_to_upload"

type OrgDistributorInsert = {
  org_id: string
  distributor: string
  start_date: string | null
  is_supported: boolean
}

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
  line: "#E6DDCB",
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

function hasSixFullMonths(
    startDate: StartDate
  ): boolean {
    if (!startDate.month || !startDate.year) {
      return false
    }

    const startMonthIndex =
      months.indexOf(startDate.month)

    if (startMonthIndex === -1) {
      return false
    }

    const now = new Date()

    const currentYear = now.getFullYear()
    const currentMonthIndex = now.getMonth()

    const startYear = Number(startDate.year)

    const monthsSinceStart =
      (currentYear - startYear) * 12 +
      (currentMonthIndex - startMonthIndex)

    return monthsSinceStart >= 6
  }

export default function FreeTrialStartPage() {
  const router = useRouter()

  const [submissionId, setSubmissionId] =
    useState<string | null>(null)

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

  const [leadModalType, setLeadModalType] =
  useState<LeadModalType>(null)

  const [leadEmail, setLeadEmail] =
    useState("")

  const [leadSubmitted, setLeadSubmitted] =
    useState(false)

  const [leadError, setLeadError] =
    useState<string | null>(null)

  const [isSubmittingLead, setIsSubmittingLead] =
    useState(false)

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

async function captureFreeTrialSubmission(
    outcome: "short_history" | "other_only" | "proceeded_to_upload"
  ) {
    const newSubmissionId = crypto.randomUUID()

    const { error: insertError } = await supabase
      .from("free_trial_submissions")
      .insert({
        id: newSubmissionId,
        brand_name: brandName.trim(),
        distributors,
        other_distributors: otherDistributors.trim() || null,

        kehe_start_month:
          distributors.includes("kehe")
            ? keheStart.month || null
            : null,
        kehe_start_year:
          distributors.includes("kehe")
            ? keheStart.year || null
            : null,

        unfi_start_month:
          distributors.includes("unfi")
            ? unfiStart.month || null
            : null,
        unfi_start_year:
          distributors.includes("unfi")
            ? unfiStart.year || null
            : null,

        outcome,
      })

    if (insertError) {
      console.error(
        "FREE TRIAL SUBMISSION ERROR:",
        insertError
      )
      return null
    }

    setSubmissionId(newSubmissionId)
    return newSubmissionId
  }

  async function handleBusinessContinue() {
    setError(null)
    setLeadSubmitted(false)
    setLeadError(null)

    if (!brandName.trim()) {
      setError("Enter your brand name.")
      return
    }

    if (distributors.length === 0) {
      setError("Select at least one distributor.")
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

    const hasKehe =
      distributors.includes("kehe")

    const hasUnfi =
      distributors.includes("unfi")

    const hasSupportedDistributor =
      hasKehe || hasUnfi

    /*
     * OTHER ONLY
     */

    if (!hasSupportedDistributor) {
      await captureFreeTrialSubmission("other_only")
      setLeadModalType("other_distributor")
      return
    }

    /*
     * Validate dates for supported distributors.
     */

    if (
      hasKehe &&
      (!keheStart.month || !keheStart.year)
    ) {
      setError(
        "Tell us when you started working with KeHE."
      )
      return
    }

    if (
      hasUnfi &&
      (!unfiStart.month || !unfiStart.year)
    ) {
      setError(
        "Tell us when you started working with UNFI."
      )
      return
    }

    /*
     * At least ONE supported distributor must
     * have 6 full months of history.
     */

    const hasEnoughHistory =
      (hasKehe && hasSixFullMonths(keheStart)) ||
      (hasUnfi && hasSixFullMonths(unfiStart))

    if (!hasEnoughHistory) {
      await captureFreeTrialSubmission("short_history")
      setLeadModalType("short_history")
      return
    }

    /*
     * Eligible for normal self-serve free analysis.
     */

    await captureFreeTrialSubmission(
      "proceeded_to_upload"
    )

    setStep("activate")
  }

  async function handleLeadSubmit() {
    setLeadError(null)

    const trimmedEmail = leadEmail.trim()

    if (!trimmedEmail) {
      setLeadError("Enter your work email.")
      return
    }

    if (!leadModalType) {
      return
    }

    if (!submissionId) {
      setLeadError(
        "Something went wrong. Please try again."
      )
      return
    }

    setIsSubmittingLead(true)

    try {
      const { error: updateError } = await supabase.rpc(
        "add_free_trial_submission_email",
        {
          p_submission_id: submissionId,
          p_email: trimmedEmail,
        }
      )

      if (updateError) {
        console.error(
          "FREE TRIAL EMAIL UPDATE ERROR:",
          updateError
        )

        setLeadError(
          "Something went wrong. Please try again."
        )

        return
      }

      setLeadSubmitted(true)
    } catch (error) {
      console.error(error)

      setLeadError(
        "Something went wrong. Please try again."
      )
    } finally {
      setIsSubmittingLead(false)
    }
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
          backgroundColor: theme.cream,
          color: theme.ink,
          fontFamily: "'Figtree', system-ui, sans-serif",
        }}
      >
        <style jsx global>{`
          @import url("https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Figtree:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap");
          .skuba-display { font-family: "Baloo 2", cursive; }
        `}</style>

        <div className="mx-auto max-w-6xl">
          <div className="flex items-center justify-between">
            <p className="skuba-display text-[30px] font-extrabold tracking-[-0.03em]" style={{ color: theme.coral }}>SKUba</p>
            <div className="hidden items-center gap-2 rounded-full px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.13em] md:flex" style={{ backgroundColor: theme.creamDeep, color: theme.slate }}>
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: theme.sageInk }} />
              Built for emerging CPG brands
            </div>
          </div>

          <div className="grid min-h-[calc(100vh-120px)] items-center gap-14 py-12 lg:grid-cols-[1.03fr_0.97fr] lg:gap-16">
            <div>
              <div className="skuba-display inline-flex items-center rounded-full px-4 py-2 text-[12px] font-bold uppercase tracking-[0.12em]" style={{ backgroundColor: theme.creamDeep, color: theme.slate }}>
                Free distributor data analysis
              </div>
              <h1 className="skuba-display mt-6 max-w-[680px] text-[50px] font-extrabold leading-[1.02] tracking-[-0.035em] md:text-[68px]" style={{ color: theme.ink }}>
                Let&apos;s find what&apos;s <span style={{ color: theme.coralDark }}>hiding</span> in your distributor data.
              </h1>
              <p className="mt-6 max-w-[590px] text-[18px] leading-[1.7]" style={{ color: theme.slate }}>
                Upload your UNFI and KeHE data. SKUba will clean it, combine it, and surface the risks, opportunities, and changes worth your attention.
              </p>
              <div className="mt-9 flex flex-wrap items-center gap-5">
                <button type="button" onClick={() => setStep("business")} className="skuba-display inline-flex items-center gap-2 rounded-full border-2 px-6 py-3.5 text-[16px] font-bold transition-transform hover:translate-x-[1px] hover:translate-y-[1px]" style={{ backgroundColor: theme.coral, borderColor: theme.ink, color: "#FFFFFF", boxShadow: `4px 4px 0 ${theme.ink}` }}>
                  Start my free analysis <ArrowRight size={17} />
                </button>
                <p className="text-[12px]" style={{ color: theme.slate }}>No credit card required.</p>
              </div>
            </div>

            <div className="relative pb-10">
              <div className="rounded-[28px] border-2 px-6 py-6 md:px-7 md:py-7" style={{ backgroundColor: theme.paper, borderColor: theme.ink, boxShadow: `8px 8px 0 ${theme.creamDeep}, 0 12px 30px rgba(34,51,59,.08)` }}>
                <div className="flex items-center gap-3">
                  <span className="h-[3px] w-8 rounded-full" style={{ backgroundColor: theme.coral }} />
                  <p className="text-[11px] font-bold uppercase tracking-[0.16em]" style={{ color: theme.slate }}>What needs your attention</p>
                </div>
                <p className="skuba-display mt-2 text-[24px] font-extrabold leading-tight" style={{ color: theme.ink }}>SKUba found 8 things worth reviewing.</p>

                <div className="mt-6 space-y-4">
                  <div className="rounded-[18px] border-2 p-5" style={{ borderColor: theme.creamDeep, backgroundColor: "#FFFEFB" }}>
                    <div className="flex items-center justify-between gap-4">
                      <span className="rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em]" style={{ backgroundColor: "#FBE3DC", color: theme.coralDark }}>At risk</span>
                      <span className="text-[11px] font-medium" style={{ color: theme.slate }}>Sprouts</span>
                    </div>
                    <p className="mt-3 text-[16px] font-medium leading-[1.5]" style={{ color: theme.ink }}>Sprouts has a higher concentration of struggling stores than the rest of the business.</p>
                    <div className="mt-5 flex flex-wrap gap-2">
                      {Array.from({ length: 11 }).map((_, index) => (
                        <span key={index} className="h-4 w-4 rounded-[4px] border" style={{ backgroundColor: index < 6 ? theme.coral : "transparent", borderColor: index < 6 ? theme.coral : theme.creamDeep }} />
                      ))}
                    </div>
                    <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-[12px]">
                      <span style={{ color: theme.slate }}>6 of 11 stores struggling</span>
                      <span className="font-semibold" style={{ color: theme.coralDark }}>+45 pts vs. average</span>
                    </div>
                  </div>

                  <div className="rounded-[18px] border-2 p-5" style={{ borderColor: theme.creamDeep, backgroundColor: "#FFFEFB" }}>
                    <span className="rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em]" style={{ backgroundColor: theme.amberBg, color: theme.amberInk }}>Opportunity</span>
                    <p className="mt-3 text-[16px] font-medium leading-[1.5]" style={{ color: theme.ink }}>Peanut Butter isn&apos;t sold in 63 ShopRite stores already buying your brand.</p>
                    <div className="mt-4 flex items-baseline gap-2">
                      <span className="skuba-display text-[26px] font-extrabold" style={{ color: theme.coralDark }}>~2,464</span>
                      <span className="text-[12px]" style={{ color: theme.slate }}>annualized units of potential upside</span>
                    </div>
                  </div>
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
          backgroundColor: theme.cream,
          color: theme.ink,
          fontFamily: "'Figtree', system-ui, sans-serif",
        }}
      >
        <style jsx global>{`
          @import url("https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Figtree:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap");

          .skuba-display {
            font-family: "Baloo 2", cursive;
          }
        `}</style>

        <div className="mx-auto max-w-2xl">
          {/* LOGO */}

          <div className="mb-8 text-center">
            <p
              className="skuba-display text-[30px] font-extrabold tracking-[-0.03em]"
              style={{ color: theme.coral }}
            >
              SKUba
            </p>
          </div>

          {/* BACK */}

          <button
            type="button"
            onClick={() => setStep("business")}
            className="mb-5 text-[13px] font-medium"
            style={{ color: theme.slate }}
          >
            ← Back
          </button>

          {/* CARD */}

          <div
            className="rounded-[28px] border-2 px-7 py-10 md:px-10 md:py-12"
            style={{
              backgroundColor: theme.paper,
              borderColor: theme.ink,
              boxShadow: `7px 7px 0 ${theme.creamDeep}`,
            }}
          >
            {/* INTRO */}

            <div>
              <div
                className="skuba-display inline-flex rounded-full px-4 py-2 text-[11px] font-bold uppercase tracking-[0.13em]"
                style={{
                  backgroundColor: theme.creamDeep,
                  color: theme.slate,
                }}
              >
                Almost there
              </div>

              <h1
                className="skuba-display mt-4 text-[38px] font-extrabold leading-tight tracking-[-0.025em]"
                style={{ color: theme.ink }}
              >
                Activate your free analysis.
              </h1>

              <p
                className="mt-3 max-w-xl text-[15px] leading-[1.7]"
                style={{ color: theme.slate }}
              >
                Create a login so we can save your{" "}
                <span
                  className="font-semibold"
                  style={{ color: theme.ink }}
                >
                  {brandName}
                </span>{" "}
                analysis and let you come back to your results.
              </p>
            </div>

            <div className="mt-8 space-y-5">
              {/* EMAIL */}

              <div>
                <label
                  htmlFor="email"
                  className="mb-2 block text-[14px] font-semibold"
                  style={{ color: theme.ink }}
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
                  className="w-full rounded-[14px] border-2 px-4 py-3 text-[16px] outline-none transition"
                  style={{
                    borderColor: theme.creamDeep,
                    backgroundColor: "#FFFEFB",
                    color: theme.ink,
                  }}
                />
              </div>

              {/* PASSWORD */}

              <div>
                <label
                  htmlFor="password"
                  className="mb-2 block text-[14px] font-semibold"
                  style={{ color: theme.ink }}
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
                  className="w-full rounded-[14px] border-2 px-4 py-3 text-[16px] outline-none transition"
                  style={{
                    borderColor: theme.creamDeep,
                    backgroundColor: "#FFFEFB",
                    color: theme.ink,
                  }}
                />

                <p
                  className="mt-2 text-[12px]"
                  style={{ color: theme.slate }}
                >
                  Your account keeps your uploaded data and analysis tied
                  to your brand.
                </p>
              </div>

              {/* ERROR */}

              {activationError && (
                <div
                  className="rounded-[14px] border-2 px-4 py-3 text-[13px]"
                  style={{
                    backgroundColor: "#FFF1EC",
                    borderColor: "#F3C9BC",
                    color: theme.coralDark,
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
                className="skuba-display mt-2 inline-flex w-full items-center justify-center gap-2 rounded-full border-2 px-6 py-3.5 text-[16px] font-bold transition-transform disabled:cursor-not-allowed disabled:opacity-60"
                style={{
                  backgroundColor: theme.coral,
                  borderColor: theme.ink,
                  color: "#FFFFFF",
                  boxShadow: `4px 4px 0 ${theme.ink}`,
                }}
              >
                {isActivating
                  ? "Creating your analysis..."
                  : "Create account & continue"}

                {!isActivating && (
                  <ArrowRight size={17} />
                )}
              </button>

              <p
                className="text-center text-[12px] leading-relaxed"
                style={{ color: theme.slate }}
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
        backgroundColor: theme.cream,
        color: theme.ink,
        fontFamily: "'Figtree', system-ui, sans-serif",
      }}
    >
      <style jsx global>{`
        @import url("https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Figtree:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap");

        .skuba-display {
          font-family: "Baloo 2", cursive;
        }
      `}</style>

      <div className="mx-auto max-w-2xl">
        <div className="mb-8 text-center">
          <p
            className="skuba-display text-[30px] font-extrabold tracking-[-0.03em]"
            style={{ color: theme.coral }}
          >
            SKUba
          </p>
        </div>

        <button
          type="button"
          onClick={() => setStep("welcome")}
          className="mb-5 text-[13px] font-medium"
          style={{ color: theme.slate }}
        >
          ← Back
        </button>

        <div
          className="rounded-[28px] border-2 px-7 py-9 md:px-10 md:py-11"
          style={{
            backgroundColor: theme.paper,
            borderColor: theme.ink,
            boxShadow: `7px 7px 0 ${theme.creamDeep}`,
          }}
        >
          <div className="mb-9">
            <div
              className="skuba-display inline-flex rounded-full px-4 py-2 text-[11px] font-bold uppercase tracking-[0.13em]"
              style={{
                backgroundColor: theme.creamDeep,
                color: theme.slate,
              }}
            >
              First, a little context
            </div>

            <h1
              className="skuba-display mt-4 text-[38px] font-extrabold leading-tight tracking-[-0.025em]"
              style={{ color: theme.ink }}
            >
              Tell us about your business.
            </h1>

            <p
              className="mt-3 max-w-xl text-[15px] leading-[1.7]"
              style={{ color: theme.slate }}
            >
              This helps SKUba understand your distributor history and analyze
              your data correctly.
            </p>
          </div>

          <div className="space-y-8">
            <div>
              <label
                htmlFor="brand-name"
                className="mb-2 block text-[14px] font-semibold"
                style={{ color: theme.ink }}
              >
                Brand name
              </label>

              <input
                id="brand-name"
                type="text"
                value={brandName}
                onChange={(event) => setBrandName(event.target.value)}
                placeholder="e.g. Goodles"
                className="w-full rounded-[14px] border-2 px-4 py-3 text-[16px] outline-none"
                style={{
                  borderColor: theme.creamDeep,
                  backgroundColor: "#FFFEFB",
                  color: theme.ink,
                }}
              />
            </div>

            <div>
              <p
                className="text-[14px] font-semibold"
                style={{ color: theme.ink }}
              >
                Which distributors do you work with?
              </p>

              <p
                className="mt-1 text-[13px]"
                style={{ color: theme.slate }}
              >
                Select all that apply.
              </p>

              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <DistributorButton
                  label="KeHE"
                  selected={distributors.includes("kehe")}
                  onClick={() => toggleDistributor("kehe")}
                />

                <DistributorButton
                  label="UNFI"
                  selected={distributors.includes("unfi")}
                  onClick={() => toggleDistributor("unfi")}
                />

                <DistributorButton
                  label="Other"
                  selected={distributors.includes("other")}
                  onClick={() => toggleDistributor("other")}
                />
              </div>

                {distributors.includes("other") && (
                  <>
                    <div className="mt-4">
                      <label
                        htmlFor="other-distributors"
                        className="mb-2 block text-[13px] font-semibold"
                        style={{ color: theme.ink }}
                      >
                        Which other distributors?
                      </label>

                      <input
                        id="other-distributors"
                        type="text"
                        value={otherDistributors}
                        onChange={(event) =>
                          setOtherDistributors(event.target.value)
                        }
                        placeholder="e.g. Dot Foods, McLane"
                        className="w-full rounded-[14px] border-2 px-4 py-3 text-[16px] outline-none"
                        style={{
                          borderColor: theme.creamDeep,
                          backgroundColor: "#FFFEFB",
                          color: theme.ink,
                        }}
                      />
                    </div>

                    {(distributors.includes("kehe") ||
                      distributors.includes("unfi")) && (
                      <div
                        className="mt-4 rounded-[16px] border-2 px-4 py-3"
                        style={{
                          backgroundColor: theme.paper,
                          borderColor: theme.creamDeep,
                        }}
                      >
                        <p
                          className="text-[13px] leading-[1.65]"
                          style={{ color: theme.slate }}
                        >
                          Self-serve setup currently covers UNFI and KeHE.
                          Your other distributor won&apos;t be included in this
                          analysis, but we can help add it separately.
                        </p>
                      </div>
                    )}
                  </>
                )}
              </div>

            {distributors.includes("kehe") && (
              <DistributorStartDate
                distributor="KeHE"
                value={keheStart}
                onChange={setKeheStart}
              />
            )}

            {distributors.includes("unfi") && (
              <DistributorStartDate
                distributor="UNFI"
                value={unfiStart}
                onChange={setUnfiStart}
              />
            )}

            {error && (
              <div
                className="rounded-[14px] border-2 px-4 py-3 text-[13px]"
                style={{
                  backgroundColor: "#FFF1EC",
                  borderColor: "#F3C9BC",
                  color: theme.coralDark,
                }}
              >
                {error}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={handleBusinessContinue}
                className="skuba-display inline-flex items-center gap-2 rounded-full border-2 px-6 py-3 text-[16px] font-bold"
                style={{
                  backgroundColor: theme.coral,
                  borderColor: theme.ink,
                  color: "#FFFFFF",
                  boxShadow: `4px 4px 0 ${theme.ink}`,
                }}
              >
                Continue
                <ArrowRight size={16} />
              </button>
            </div>

          </div>
        </div>
      </div>

      {leadModalType && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#22333B]/35 px-5"
          onClick={() => {
            if (!isSubmittingLead) {
              setLeadModalType(null)
              setLeadSubmitted(false)
              setLeadError(null)
            }
          }}
        >
          <div
            className="w-full max-w-lg rounded-[28px] border-2 px-7 py-8 md:px-9"
            style={{
              backgroundColor: theme.paper,
              borderColor: theme.ink,
              boxShadow: `7px 7px 0 ${theme.creamDeep}`,
            }}
            onClick={(event) =>
              event.stopPropagation()
            }
          >
            {leadSubmitted ? (
              <>
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-full"
                  style={{
                    backgroundColor: theme.sageBg,
                    color: theme.sageInk,
                  }}
                >
                  <Check size={20} />
                </div>

                <h2
                  className="skuba-display mt-5 text-[30px] font-extrabold leading-tight"
                  style={{ color: theme.ink }}
                >
                  You're on the list.
                </h2>

                <p
                  className="mt-3 text-[15px] leading-[1.7]"
                  style={{ color: theme.slate }}
                >
                  We&apos;ll reach out shortly to help get
                  you set up.
                </p>

                <button
                  type="button"
                  onClick={() => {
                    setLeadModalType(null)
                    setLeadSubmitted(false)
                  }}
                  className="skuba-display mt-7 inline-flex rounded-full border-2 px-6 py-3 text-[15px] font-bold"
                  style={{
                    backgroundColor: theme.coral,
                    borderColor: theme.ink,
                    color: "#FFFFFF",
                    boxShadow: `3px 3px 0 ${theme.ink}`,
                  }}
                >
                  Done
                </button>
              </>
            ) : (
              <>
                <div
                  className="mb-3 h-1 w-12 rounded-full"
                  style={{
                    backgroundColor: theme.coral,
                  }}
                />

                <h2
                  className="skuba-display text-[30px] font-extrabold leading-tight"
                  style={{ color: theme.ink }}
                >
                  {leadModalType === "short_history"
                    ? "Your data is still building"
                    : "Your free trial starts with your data"}
                </h2>

                {leadModalType === "short_history" ? (
                  <>
                    <p
                      className="mt-4 text-[15px] leading-[1.7]"
                      style={{ color: theme.slate }}
                    >
                      SKUba&apos;s{" "}
                      <span
                        className="font-semibold"
                        style={{ color: theme.ink }}
                      >
                        Insights and Monitoring
                      </span>{" "}
                      features work best when you have at
                      least{" "}
                      <span
                        className="font-semibold"
                        style={{ color: theme.ink }}
                      >
                        6 months of data from one distributor.
                      </span>
                    </p>

                    <p
                      className="mt-3 text-[15px] leading-[1.7]"
                      style={{ color: theme.slate }}
                    >
                      You don&apos;t have that much history
                      yet, but we can still set you up with a{" "}
                      <span
                        className="font-semibold"
                        style={{ color: theme.ink }}
                      >
                        free dashboard
                      </span>{" "}
                      so you can explore your distributor
                      data as it grows.
                    </p>
                  </>
                ) : (
                  <>
                    <p
                      className="mt-4 text-[15px] leading-[1.7]"
                      style={{ color: theme.slate }}
                    >
                      We can run a free trial with your distributor data.
                      Before you continue, we&apos;ll need to take a quick
                      look at one of your distributor reports so we can get
                      everything ready for you.
                    </p>

                    <p
                      className="mt-3 text-[15px] leading-[1.7]"
                      style={{ color: theme.slate }}
                    >
                      Enter your email below and we&apos;ll reach out with
                      where to send it. Once it&apos;s set up, you&apos;ll
                      be able to continue your free trial.
                    </p>

                    <p
                      className="mt-4 text-[12px] leading-[1.6]"
                      style={{ color: theme.slate }}
                    >
                      Self-serve setup is currently available for UNFI and KeHE.
                    </p>
                  </>
                )}

                <div className="mt-6">
                  <label
                    htmlFor="lead-email"
                    className="mb-2 block text-[13px] font-semibold"
                    style={{ color: theme.ink }}
                  >
                    Work email
                  </label>

                  <input
                    id="lead-email"
                    type="email"
                    value={leadEmail}
                    onChange={(event) =>
                      setLeadEmail(event.target.value)
                    }
                    placeholder="you@brand.com"
                    className="w-full rounded-[14px] border-2 px-4 py-3 text-[16px] outline-none"
                    style={{
                      backgroundColor: "#FFFEFB",
                      borderColor: theme.creamDeep,
                      color: theme.ink,
                    }}
                  />
                </div>

                {leadError && (
                  <div
                    className="mt-3 rounded-[14px] border-2 px-4 py-3 text-[13px]"
                    style={{
                      backgroundColor: "#FFF1EC",
                      borderColor: "#F3C9BC",
                      color: theme.coralDark,
                    }}
                  >
                    {leadError}
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleLeadSubmit}
                  disabled={isSubmittingLead}
                  className="skuba-display mt-5 inline-flex w-full items-center justify-center gap-2 rounded-full border-2 px-6 py-3.5 text-[16px] font-bold disabled:cursor-not-allowed disabled:opacity-60"
                  style={{
                    backgroundColor: theme.coral,
                    borderColor: theme.ink,
                    color: "#FFFFFF",
                    boxShadow: `4px 4px 0 ${theme.ink}`,
                  }}
                >
                  {isSubmittingLead
                    ? "Sending..."
                    : leadModalType === "short_history"
                      ? "Get my free dashboard"
                      : "Send me the next step"}

                  {!isSubmittingLead && (
                    <ArrowRight size={17} />
                  )}
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setLeadModalType(null)
                  }
                  className="mt-4 w-full text-center text-[12px] font-medium"
                  style={{ color: theme.slate }}
                >
                  Not right now
                </button>
              </>
            )}
          </div>
        </div>
      )}
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
      className="flex min-h-[58px] items-center justify-between rounded-[16px] border-2 px-4 text-left text-[15px] font-semibold transition"
      style={{
        backgroundColor: selected
          ? "#FFF1EC"
          : "#FFFEFB",

        borderColor: selected
          ? theme.coral
          : theme.creamDeep,

        color: theme.ink,
      }}
    >
      {label}

      <span
        className="h-3 w-3 rounded-full"
        style={{
          backgroundColor: selected
            ? theme.coral
            : theme.creamDeep,
        }}
      />
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
          color: theme.ink,
        }}
      >
        When did you start working with{" "}
        {distributor}?
      </p>

      <p
        className="mt-1 text-[13px] leading-relaxed"
        style={{
          color: theme.slate,
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
              ? theme.ink
              : theme.slate,
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
              ? theme.ink
              : theme.slate,
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