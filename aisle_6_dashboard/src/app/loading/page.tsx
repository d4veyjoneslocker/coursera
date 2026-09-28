"use client";

import { useState } from "react";
import LoadingScreen from "@/components/LoadingScreen";

type LoadingMode =
  | "setup"
  | "upload"
  | "processing"
  | "results"
  | "inventory-overview"
  | "store"
  | "export"
  | "dc-network"
  | "dc-detail";

const modes: { value: LoadingMode; label: string }[] = [
  { value: "setup", label: "Setup" },
  { value: "upload", label: "Upload" },
  { value: "processing", label: "Processing" },
  { value: "results", label: "Results" },
  { value: "inventory-overview", label: "Inventory Overview" },
  { value: "store", label: "Store" },
  { value: "export", label: "Export" },
  { value: "dc-network", label: "DC Network" },
  { value: "dc-detail", label: "DC Detail" },
];

export default function LoadingPage() {
  const [mode, setMode] =
    useState<LoadingMode>("inventory-overview");

  return (
    <div className="relative min-h-screen">
      <LoadingScreen mode={mode} />

      {/* Loading screen selector */}
      <div className="fixed left-6 top-6 z-50">
        <div className="rounded-2xl border border-black/[0.06] bg-white/90 p-2 shadow-[0_8px_30px_rgba(34,51,59,0.10)] backdrop-blur-xl">
          <div className="px-2 pb-1.5 pt-1">
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#48605F]/60">
              Loading Screen
            </p>
          </div>

          <div className="relative">
            <select
              value={mode}
              onChange={(e) =>
                setMode(e.target.value as LoadingMode)
              }
              className="min-w-[190px] cursor-pointer appearance-none rounded-xl border border-black/[0.07] bg-[#F8F6F0] py-2.5 pl-3.5 pr-10 text-[14px] font-semibold text-[#22333B] outline-none transition hover:bg-[#F4F0E5] focus:border-[#EE6A4C]/40 focus:ring-2 focus:ring-[#EE6A4C]/10"
            >
              {modes.map((option) => (
                <option
                  key={option.value}
                  value={option.value}
                >
                  {option.label}
                </option>
              ))}
            </select>

            {/* Custom chevron */}
            <svg
              viewBox="0 0 20 20"
              fill="none"
              aria-hidden="true"
              className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#48605F]"
            >
              <path
                d="M6 8L10 12L14 8"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}