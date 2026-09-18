"use client";

import { useEffect, useState } from "react";

type LoadingMode = "setup" | "upload" | "processing" | "results" | "inventory-overview" | "dc-network" | "dc-detail";

type LoadingConfig = {
  headline: string;
  messages: string[];
  slowMessage: string;
};

const loadingConfigs: Record<LoadingMode, LoadingConfig> = {
  setup: {
    headline: "Getting things ready",
    messages: [
      "Setting up your free analysis...",
      "Getting your workspace ready...",
      "Almost ready for your distributor data...",
    ],
    slowMessage:
      "Still working — this should only take a moment.",
  },

  upload: {
    headline: "Getting your data ready",
    messages: [
      "Reading your distributor reports...",
      "Checking your uploads...",
      "Organizing your distributor data...",
    ],
    slowMessage:
      "Still working — larger distributor files can take a little longer.",
  },

  processing: {
    headline: "Diving into your distributor data",
    messages: [
      "Checking reorder patterns...",
      "Scanning velocity changes...",
      "Looking across stores and SKUs...",
      "Surfacing hidden opportunities...",
    ],
    slowMessage:
      "Still diving — there’s a lot of distributor data to explore.",
  },

  results: {
    headline: "Getting your insights ready",
    messages: [
      "Pulling together your findings...",
      "Prioritizing what needs your attention...",
      "Putting the finishing touches on your analysis...",
    ],
    slowMessage:
      "Almost there — we’re finishing up your analysis.",
  },

  "inventory-overview": {
    headline: "Checking your inventory",
    messages: [
      "Reviewing inventory across your network...",
      "Checking upcoming inventory needs...",
      "Prioritizing what needs your attention...",
      "Looking for supply risks...",
    ],
    slowMessage:
      "Still checking — we're working through your inventory network.",
  },

  "dc-network": {
    headline: "Loading your DC network",
    messages: [
      "Pulling together your distribution centers...",
      "Checking inventory across your network...",
      "Mapping your distribution centers and stores...",
      "Getting your network view ready...",
    ],
    slowMessage:
      "Still loading — we're pulling together your distribution network.",
  },

  "dc-detail": {
    headline: "Loading distribution center",
    messages: [
      "Pulling the latest inventory...",
      "Checking SKU inventory levels...",
      "Loading supply and PO activity...",
      "Building your inventory outlook...",
    ],
    slowMessage:
      "Still loading — we're finishing up this distribution center.",
  },
};

export default function LoadingScreen({
  mode = "setup",
}: {
  mode?: LoadingMode;
}) {
  const [messageIndex, setMessageIndex] = useState(0);
  const [slow, setSlow] = useState(false);

  const config = loadingConfigs[mode];

  useEffect(() => {
    setMessageIndex(0);
    setSlow(false);

    const messageTimer = setInterval(() => {
      setMessageIndex(
        (prev) => (prev + 1) % config.messages.length
      );
    }, 1800);

    const slowTimer = setTimeout(() => {
      setSlow(true);
    }, 8000);

    return () => {
      clearInterval(messageTimer);
      clearTimeout(slowTimer);
    };
  }, [mode, config.messages.length]);

  return (
    <div
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-[#F4F0E5] px-6 text-center"
      style={{
        fontFamily: "'Figtree', system-ui, sans-serif",
      }}
    >
      <style jsx global>{`
        @import url("https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Figtree:wght@400;500;600;700&display=swap");

        .skuba-display {
          font-family: "Baloo 2", cursive;
        }
      `}</style>

      {/* Background glow */}
      <div className="absolute -left-24 top-24 h-72 w-72 rounded-full bg-white/30 blur-3xl" />
      <div className="absolute -right-24 bottom-24 h-72 w-72 rounded-full bg-[#ECE6D6]/50 blur-3xl" />

      {/* Bubbles */}
      <div className="absolute bottom-12 left-[18%] h-3 w-3 rounded-full bg-white/50 animate-bubble" />
      <div className="absolute bottom-24 left-[24%] h-2 w-2 rounded-full bg-white/40 animate-bubble-slow" />
      <div className="absolute bottom-16 right-[18%] h-4 w-4 rounded-full bg-white/35 animate-bubble" />
      <div className="absolute bottom-28 right-[26%] h-2 w-2 rounded-full bg-white/45 animate-bubble-slow" />

      {/* Octopus */}
      <div className="relative">
        <div className="absolute inset-0 scale-125 rounded-full bg-[#ECE6D6]/50 blur-3xl" />

        <img
          src="/octopus-loading.png"
          alt="Loading"
          draggable={false}
          className="relative h-64 w-64 select-none animate-skuba-float"
        />
      </div>

      <h2 className="skuba-display mt-3 text-3xl font-bold tracking-tight text-[#22333B]">
        {config.headline}
      </h2>

      <p className="skuba-display mt-2 h-7 text-[17px] font-semibold text-[#48605F] transition-all duration-300">
        {config.messages[messageIndex]}
      </p>

      {/* Loading bar */}
      <div className="mt-5 h-2 w-80 overflow-hidden rounded-full bg-white/70 shadow-sm">
        <div className="h-full w-1/3 rounded-full bg-[#EE6A4C] animate-skuba-shimmer" />
      </div>

      {slow && (
        <p className="mt-4 max-w-sm text-sm text-[#48605F]">
          {config.slowMessage}
        </p>
      )}
    </div>
  );
}