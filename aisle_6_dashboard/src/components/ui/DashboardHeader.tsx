"use client"

import Image from "next/image"

type DashboardHeaderProps = {
  brandName: string
  subtitle?: string
  logoSrc?: string
  lastUpdated?: string
}

const theme = {
  charcoal: "#343332",
  line: "#E5DDD0",
}

export default function DashboardHeader({
  brandName,
  subtitle = "Sales Dashboard",
  logoSrc,
  lastUpdated,
}: DashboardHeaderProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        {/* LEFT SIDE */}
        <div className="flex items-center gap-3">
          {/* LOGO */}
          <div className="flex items-center justify-center">
            {logoSrc ? (
              <Image
                src={logoSrc}
                alt={`${brandName} logo`}
                width={48}
                height={48}
                className="h-12 w-auto object-contain"
              />
            ) : (
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#F3EEE6]">
                <span
                  className="text-base font-semibold"
                  style={{ color: theme.charcoal }}
                >
                  {brandName.slice(0, 2).toUpperCase()}
                </span>
              </div>
            )}
          </div>

          {/* BRAND TEXT */}
          <div>
            <h1
              className="text-[28px] font-semibold leading-none tracking-tight"
              style={{ color: theme.charcoal }}
            >
              {brandName}
            </h1>

            <p
              className="mt-1 text-[12px] uppercase tracking-[0.18em]"
              style={{ color: "#7A746B" }}
            >
              {subtitle}
            </p>
          </div>
        </div>



        {/* RIGHT SIDE */}
        
        <div className="flex items-center gap-3">
          {/*
          <button
            className="rounded-full border px-3 py-1.5 text-xs font-medium"
            style={{
              borderColor: "#D8CFBF",
              color: "#705C4F",
              backgroundColor: "#FAF7F1",
            }}
          >
            Pages ▾
          </button>

          <button
            className="rounded-full border px-3 py-1.5 text-xs font-medium"
            style={{
              borderColor: "#D8CFBF",
              color: "#705C4F",
              backgroundColor: "#FAF7F1",
            }}
          >
            Actions ▾
          </button>
          */}


          {/* DATE + STATUS STACK */}
          <div className="ml-3 flex flex-col items-end text-right">
            {lastUpdated && (
              <p
                className="pr-3 text-xs font-medium"
                style={{ color: "#7A746B" }}
              >
                {lastUpdated}
              </p>
            )}

            <div
              className="mt-1 inline-flex items-center gap-2 self-end rounded-full px-3 py-1 text-[11px] font-medium"
              style={{
                backgroundColor: "#EAF6EE",
                color: "#2E7D32",
              }}
            >
              <div className="h-2 w-2 rounded-full bg-green-600" />
              Data loaded
            </div>
          </div>
        </div>
      </div>

      {/* SUBTLE DIVIDER */}
      <div
        className="h-[1px] w-full"
        style={{ backgroundColor: theme.line }}
      />
    </div>
  )
}