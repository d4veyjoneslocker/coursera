"use client"

import Image from "next/image"
import Link from "next/link"

type DashboardPage = "overview" | "store-health"

type DashboardHeaderProps = {
  brandName: string
  subtitle?: string
  logoSrc?: string
  lastUpdated?: string
  activePage: DashboardPage
}

const theme = {
  blue: "#92B9DC",
  gold: "#F7B045",
  brown: "#705C4F",
  charcoal: "#343332",
  line: "#E5DDD0",
  muted: "#7A746B",
  greenBg: "#EAF6EE",
  greenText: "#2E7D32",
}

const pages: { label: string; value: DashboardPage; href: string }[] = [
  { label: "Overview", value: "overview", href: "/" },
  { label: "Store Health", value: "store-health", href: "/store_health" },
]

export default function DashboardHeader({
  brandName,
  subtitle = "Sales Dashboard",
  logoSrc,
  lastUpdated,
  activePage,
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
              style={{ color: theme.muted }}
            >
              {subtitle}
            </p>
          </div>
        </div>

        {/* RIGHT SIDE */}
        <div className="flex items-center gap-5">
          {/* PAGE SWITCHER */}
          <div
            className="inline-flex items-center rounded-full border p-1.5"
            style={{
              borderColor: "#D8CFBF",
              backgroundColor: "#F6F1E8",
            }}
          >
            {pages.map((page) => {
              const isActive = activePage === page.value

              return (
                <Link
                  key={page.value}
                  href={page.href}
                  className="group relative rounded-full px-5 py-2.5 text-[13px] font-medium transition-all duration-200"
                  style={{
                    backgroundColor: isActive
                      ? `${theme.blue}15`
                      : "transparent",
                    color: isActive ? theme.charcoal : theme.brown,
                    boxShadow: isActive
                      ? "0 1px 2px rgba(52,51,50,0.08), inset 0 0 0 1px #E5DDD0"
                      : "none",
                  }}
                >
                  {/* LABEL */}
                  <span
                    className="relative z-10 transition-colors duration-200"
                    style={{
                      color: isActive ? theme.charcoal : theme.brown,
                    }}
                  >
                    {page.label}
                  </span>

                  {/* HOVER BACKGROUND (inactive only) */}
                  {!isActive && (
                    <span
                      className="absolute inset-0 rounded-full opacity-0 transition-all duration-200 group-hover:opacity-100"
                      style={{
                        backgroundColor: `${theme.brown}15`,
                      }}
                    />
                  )}

                  {/* ACTIVE UNDERLINE */}
                  <span
                    className="absolute left-4 right-4 bottom-1.5 h-[2px] rounded-full transition-all duration-200"
                    style={{
                      backgroundColor: theme.blue,
                      opacity: isActive ? 1 : 0,
                    }}
                  />

                  {/* HOVER UNDERLINE (inactive) */}
                  {!isActive && (
                    <span
                      className="absolute left-4 right-4 bottom-1.5 h-[2px] rounded-full opacity-0 transition-all duration-200 group-hover:opacity-60"
                      style={{
                        backgroundColor: theme.brown,
                      }}
                    />
                  )}
                </Link>
              )
            })}
          </div>

          {/* DATE + STATUS */}
          <div className="flex flex-col items-end text-right">
            {lastUpdated && (
              <p
                className="pr-2 text-xs font-medium"
                style={{ color: theme.muted }}
              >
                {lastUpdated}
              </p>
            )}

            <div
              className="mt-1 inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-medium"
              style={{
                backgroundColor: theme.greenBg,
                color: theme.greenText,
              }}
            >
              <div className="h-2 w-2 rounded-full bg-green-600" />
              Data loaded
            </div>
          </div>
        </div>
      </div>

      {/* DIVIDER */}
      <div
        className="h-[1px] w-full"
        style={{ backgroundColor: theme.line }}
      />
    </div>
  )
}