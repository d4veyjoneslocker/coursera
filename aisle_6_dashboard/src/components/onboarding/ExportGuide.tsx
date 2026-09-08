"use client"

import React, { useEffect, useState } from "react"
import { ArrowLeft, ArrowRight, X } from "lucide-react"

// =========================================================
// Types
// =========================================================

export type ExportGuideStep = {
  title: string
  description: React.ReactNode
  image: string
  imageAlt?: string
}

type ExportGuideProps = {
  distributor: string
  description: string
  steps: ExportGuideStep[]
}

// =========================================================
// Component
// =========================================================

export default function ExportGuide({
  distributor,
  description,
  steps,
}: ExportGuideProps) {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState(0)

  const currentStep = steps[step]
  const isFirstStep = step === 0
  const isLastStep = step === steps.length - 1

  // -------------------------------------------------------
  // Reset when modal closes
  // -------------------------------------------------------

  function closeGuide() {
    setOpen(false)
    setStep(0)
  }

  // -------------------------------------------------------
  // Escape key + body scroll
  // -------------------------------------------------------

  useEffect(() => {
    if (!open) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeGuide()
      }
    }

    document.addEventListener(
      "keydown",
      handleKeyDown
    )

    const previousOverflow =
      document.body.style.overflow

    document.body.style.overflow =
      "hidden"

    return () => {
      document.removeEventListener(
        "keydown",
        handleKeyDown
      )

      document.body.style.overflow =
        previousOverflow
    }
  }, [open])

  // -------------------------------------------------------
  // Guard
  // -------------------------------------------------------

  if (!steps.length) {
    return null
  }

  // =========================================================
  // Render
  // =========================================================

  return (
    <>
      {/* =====================================================
          Inline help card
      ===================================================== */}

      <div
        className="
          mb-6
          flex
          flex-col
          gap-4
          rounded-[18px]
          border
          border-[#22333B]/10
          bg-[#FDFBF5]
          px-5
          py-4
          sm:flex-row
          sm:items-center
          sm:justify-between
        "
      >
        <div>
          <p className="text-sm font-bold text-[#22333B]">
            How to export from {distributor}
          </p>

          <p className="mt-1 text-sm leading-5 text-[#48605F]">
            {description}
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            setStep(0)
            setOpen(true)
          }}
          className="
            inline-flex
            shrink-0
            items-center
            gap-1.5
            text-left
            text-sm
            font-bold
            text-[#EE6A4C]
            transition
            hover:text-[#D9532F]
          "
        >
          See step-by-step instructions
          <ArrowRight size={15} />
        </button>
      </div>

      {/* =====================================================
          Modal
      ===================================================== */}

      {open && (
        <div
          className="
            fixed
            inset-0
            z-50
            flex
            items-center
            justify-center
            bg-[#22333B]/55
            p-4
            backdrop-blur-[2px]
          "
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeGuide()
            }
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="export-guide-title"
            className="
              flex
              max-h-[92vh]
              w-full
              max-w-5xl
              flex-col
              overflow-hidden
              rounded-[28px]
              border-2
              border-[#22333B]
              bg-[#FDFBF5]
              shadow-[8px_8px_0_0_#ECE6D6]
            "
          >
            {/* ===============================================
                Modal header
            =============================================== */}

            <div
              className="
                flex
                shrink-0
                items-start
                justify-between
                gap-6
                border-b
                border-[#22333B]/10
                px-6
                py-5
                md:px-8
              "
            >
              <div>
                <div className="mb-2 flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#EE6A4C]" />

                  <p
                    className="
                      text-[10px]
                      font-bold
                      uppercase
                      tracking-[0.16em]
                      text-[#48605F]
                    "
                  >
                    {distributor} export guide
                  </p>
                </div>

                <h2
                  id="export-guide-title"
                  className="
                    font-['Baloo_2']
                    text-2xl
                    font-bold
                    leading-tight
                    tracking-[-0.02em]
                    text-[#22333B]
                    md:text-3xl
                  "
                >
                  {currentStep.title}
                </h2>
              </div>

              <button
                type="button"
                onClick={closeGuide}
                aria-label="Close export guide"
                className="
                  flex
                  h-10
                  w-10
                  shrink-0
                  items-center
                  justify-center
                  rounded-full
                  border
                  border-[#22333B]/10
                  bg-[#F4F0E5]
                  text-[#48605F]
                  transition
                  hover:border-[#22333B]/20
                  hover:text-[#22333B]
                "
              >
                <X size={18} />
              </button>
            </div>

            {/* ===============================================
                Scrollable content
            =============================================== */}

            <div className="overflow-y-auto px-6 py-6 md:px-8">
              {/* Step progress */}

              <div className="mb-5 flex items-center gap-2">
                {steps.map((_, index) => {
                  const active =
                    index === step

                  const completed =
                    index < step

                  return (
                    <div
                      key={index}
                      className={`
                        h-1.5
                        flex-1
                        rounded-full
                        transition
                        ${
                          active ||
                          completed
                            ? "bg-[#EE6A4C]"
                            : "bg-[#ECE6D6]"
                        }
                      `}
                    />
                  )
                })}
              </div>

              {/* Screenshot */}

              <div
                className="
                  overflow-hidden
                  rounded-[20px]
                  border
                  border-[#22333B]/10
                  bg-white
                "
              >
                <img
                  src={currentStep.image}
                  alt={
                    currentStep.imageAlt ??
                    currentStep.title
                  }
                  className="
                    max-h-[48vh]
                    max-w-[80%]
                    object-contain
                  "
                />
              </div>

              {/* Instruction */}

              <div
                className="
                  mt-5
                  flex
                  items-start
                  gap-4
                "
              >
                <div
                  className="
                    flex
                    h-8
                    w-8
                    shrink-0
                    items-center
                    justify-center
                    rounded-full
                    bg-[#EE6A4C]
                    text-xs
                    font-bold
                    text-white
                  "
                >
                  {step + 1}
                </div>

                <div>
                  <p className="font-['Baloo_2'] text-lg font-bold text-[#22333B]">
                    {currentStep.title}
                  </p>

                  <p className="mt-1 max-w-3xl text-sm leading-6 text-[#48605F]">
                    {currentStep.description}
                  </p>
                </div>
              </div>
            </div>

            {/* ===============================================
                Footer
            =============================================== */}

            <div
              className="
                flex
                shrink-0
                items-center
                justify-between
                gap-4
                border-t
                border-[#22333B]/10
                bg-[#F4F0E5]/60
                px-6
                py-4
                md:px-8
              "
            >
              <button
                type="button"
                disabled={isFirstStep}
                onClick={() =>
                  setStep((current) =>
                    Math.max(
                      0,
                      current - 1
                    )
                  )
                }
                className="
                  inline-flex
                  items-center
                  gap-2
                  rounded-full
                  border
                  border-[#22333B]/10
                  bg-[#FDFBF5]
                  px-4
                  py-2.5
                  text-sm
                  font-bold
                  text-[#22333B]
                  transition
                  hover:bg-white
                  disabled:cursor-not-allowed
                  disabled:opacity-30
                "
              >
                <ArrowLeft size={15} />
                Back
              </button>

              <p className="text-xs font-bold text-[#48605F]">
                {step + 1} of{" "}
                {steps.length}
              </p>

              {isLastStep ? (
                <button
                  type="button"
                  onClick={closeGuide}
                  className="
                    rounded-full
                    bg-[#EE6A4C]
                    px-5
                    py-2.5
                    text-sm
                    font-bold
                    text-white
                    transition
                    hover:bg-[#D9532F]
                  "
                >
                  Got it
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() =>
                    setStep((current) =>
                      Math.min(
                        steps.length -
                          1,
                        current + 1
                      )
                    )
                  }
                  className="
                    inline-flex
                    items-center
                    gap-2
                    rounded-full
                    bg-[#EE6A4C]
                    px-5
                    py-2.5
                    text-sm
                    font-bold
                    text-white
                    transition
                    hover:bg-[#D9532F]
                  "
                >
                  Next
                  <ArrowRight
                    size={15}
                  />
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}