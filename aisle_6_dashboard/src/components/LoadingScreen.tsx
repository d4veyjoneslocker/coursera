"use client";

import { useEffect, useState } from "react";

const messages = [
  "Connecting to distributor data...",
  "Checking reorder patterns...",
  "Scanning velocity changes...",
  "Surfacing hidden opportunities...",
];

export default function LoadingScreen() {
  const [messageIndex, setMessageIndex] = useState(0);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    const messageTimer = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % messages.length);
    }, 1800);

    const slowTimer = setTimeout(() => {
      setSlow(true);
    }, 8000);

    return () => {
      clearInterval(messageTimer);
      clearTimeout(slowTimer);
    };
  }, []);

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-[#DFEDFF] px-6 text-center">
      {/* Background glow */}
      <div className="absolute -left-24 top-24 h-72 w-72 rounded-full bg-white/30 blur-3xl" />
      <div className="absolute -right-24 bottom-24 h-72 w-72 rounded-full bg-sky-300/20 blur-3xl" />

      {/* Bubbles */}
      <div className="absolute left-[18%] bottom-12 h-3 w-3 rounded-full bg-white/50 animate-bubble" />
      <div className="absolute left-[24%] bottom-24 h-2 w-2 rounded-full bg-white/40 animate-bubble-slow" />
      <div className="absolute right-[18%] bottom-16 h-4 w-4 rounded-full bg-white/35 animate-bubble" />
      <div className="absolute right-[26%] bottom-28 h-2 w-2 rounded-full bg-white/45 animate-bubble-slow" />

      {/* Octopus */}
      <div className="relative">
        <div className="absolute inset-0 scale-125 rounded-full bg-sky-200/50 blur-3xl" />

        <img
          src="/octopus-loading.png"
          alt="Loading"
          draggable={false}
          className="relative h-64 w-64 select-none animate-skuba-float"
        />
      </div>

      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
        Diving into your distributor data
      </h2>

      <p className="mt-2 h-6 text-base font-medium text-sky-800 transition-all duration-300">
        {messages[messageIndex]}
      </p>

      {/* Loading bar */}
      <div className="mt-5 h-2 w-80 overflow-hidden rounded-full bg-white/70 shadow-sm">
        <div className="h-full w-1/3 rounded-full bg-sky-700 animate-skuba-shimmer" />
      </div>

      {slow && (
        <p className="mt-4 max-w-sm text-sm text-slate-500">
          Still working — larger distributor files can take a little longer.
        </p>
      )}
    </div>
  );
}