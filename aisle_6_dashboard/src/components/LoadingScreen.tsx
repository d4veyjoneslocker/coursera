"use client";

import { useEffect, useState } from "react";

type LoadingMode =
  | "setup"
  | "upload"
  | "processing"
  | "results"
  | "inventory-overview"
  | "store"
  | "dc-network"
  | "dc-detail"
  | "export";

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

  store: {
    headline: "Checking your stores",
    messages: [
      "Reviewing store performance...",
      "Checking sales and reorder patterns...",
      "Looking across your store network...",
      "Finding stores that need your attention...",
    ],
    slowMessage:
      "Still checking — we're working through your store network.",
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
  export: {
    headline: "Getting your export ready",
    messages: [
      "Pulling together your data...",
      "Organizing your export...",
      "Checking everything is ready...",
      "Packaging up your files...",
    ],
    slowMessage:
      "Still working — we're finishing up your export.",
  },
};

/*
 * SHARED ANIMATION SETTINGS
 *
 * Both animated sprites contain 24 frames arranged:
 *
 * 01  02  03  04
 * 05  06  07  08
 * 09  10  11  12
 * 13  14  15  16
 * 17  18  19  20
 * 21  22  23  24
 *
 * Animation plays forward, then backward.
 */
const FRAME_COUNT = 24;
const SPRITE_COLUMNS = 4;
const SPRITE_ROWS = 6;
const INVENTORY_FRAME_MS = 90;
const STORE_FRAME_MS = 115;

const ANIMATION_FRAMES = [
  ...Array.from({ length: FRAME_COUNT }, (_, i) => i),
  ...Array.from(
    { length: FRAME_COUNT - 2 },
    (_, i) => FRAME_COUNT - 2 - i
  ),
];

/*
 * INVENTORY SPRITE
 *
 * Frame: 671 × 320
 * Grid: 2684 × 1920
 */
const INVENTORY_FRAME_WIDTH = 671;
const INVENTORY_FRAME_HEIGHT = 320;
const ANALYSIS_FRAME_MS = 90;
const EXPORT_FRAME_MS = 115;

/*
 * STORE / SHELF SPRITE
 *
 * Frame: 569 × 320
 * Grid: 2276 × 1920
 */
const STORE_FRAME_WIDTH = 569;
const STORE_FRAME_HEIGHT = 320;

/*
 * ANALYSIS SPRITE
 *
 * Frame: 671 × 320
 * Grid: 2684 × 1920
 */
const ANALYSIS_FRAME_WIDTH = 671;
const ANALYSIS_FRAME_HEIGHT = 320;

/*
 * EXPORT / SETUP SPRITE
 *
 * Frame: 671 × 320
 * Grid: 2684 × 1920
 */
const EXPORT_FRAME_WIDTH = 671;
const EXPORT_FRAME_HEIGHT = 320;

export default function LoadingScreen({
  mode = "setup",
}: {
  mode?: LoadingMode;
}) {
  const [messageIndex, setMessageIndex] = useState(0);
  const [slow, setSlow] = useState(false);
  const [animationIndex, setAnimationIndex] = useState(0);

  const config = loadingConfigs[mode];

  const useInventoryAnimation =
    mode === "inventory-overview" ||
    mode === "dc-network" ||
    mode === "dc-detail";

  const useStoreAnimation =
    mode === "store";

  const useAnalysisAnimation =
    mode === "processing" || mode === "results" || mode === "upload";
  
  const useExportAnimation =
    mode === "setup" || mode === "export";

  const useAnimatedSprite =
    useInventoryAnimation ||
    useStoreAnimation ||
    useAnalysisAnimation ||
    useExportAnimation;
  /*
   * Rotate loading messages.
   */
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

  /*
   * Advance animated sprite.
   */
  useEffect(() => {
    if (!useAnimatedSprite) {
      setAnimationIndex(0);
      return;
    }

    const frameMs = useInventoryAnimation
      ? INVENTORY_FRAME_MS
      : useStoreAnimation
        ? STORE_FRAME_MS
        : useAnalysisAnimation
          ? ANALYSIS_FRAME_MS
          : EXPORT_FRAME_MS;

    const frameTimer = setInterval(() => {
      setAnimationIndex(
        (prev) => (prev + 1) % ANIMATION_FRAMES.length
      );
    }, frameMs);

    return () => {
      clearInterval(frameTimer);
    };
  }, [
    useAnimatedSprite,
    useInventoryAnimation,
    useStoreAnimation,
    useAnalysisAnimation,
    useExportAnimation,
  ]);

  const currentFrame =
    ANIMATION_FRAMES[animationIndex];

  const spriteColumn =
    currentFrame % SPRITE_COLUMNS;

  const spriteRow =
    Math.floor(currentFrame / SPRITE_COLUMNS);

  /*
   * Pick the correct sprite + frame dimensions.
   */
  const spriteConfig = useInventoryAnimation
  ? {
      src: "/loading/inventory/sprite_inventory_24_grid.png",
      frameWidth: INVENTORY_FRAME_WIDTH,
      frameHeight: INVENTORY_FRAME_HEIGHT,
      scale: 1,
      alt: "Checking inventory",
    }
  : useStoreAnimation
    ? {
        src: "/loading/store/sprite_shelf_24_grid.png",
        frameWidth: STORE_FRAME_WIDTH,
        frameHeight: STORE_FRAME_HEIGHT,
        scale: 1,
        alt: "Checking stores",
      }
    : useAnalysisAnimation
      ? {
          src: "/loading/analysis/analysis_24_grid.png",
          frameWidth: ANALYSIS_FRAME_WIDTH,
          frameHeight: ANALYSIS_FRAME_HEIGHT,
          scale: 0.85,
          alt: "Analyzing distributor data",
        }
      : useExportAnimation
        ? {
            src: "/loading/export/files_24_grid.png",
            frameWidth: EXPORT_FRAME_WIDTH,
            frameHeight: EXPORT_FRAME_HEIGHT,
            scale: 0.85,
            alt: "Organizing files",
          }
        : null;

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

      {/* Mascot */}
      <div className="relative">
        <div className="absolute inset-0 scale-125 rounded-full bg-[#ECE6D6]/50 blur-3xl" />

        {spriteConfig ? (
          <div
            role="img"
            aria-label={spriteConfig.alt}
            className="relative select-none"
            style={{
              width: `${spriteConfig.frameWidth}px`,
              height: `${spriteConfig.frameHeight}px`,
              maxWidth: "100%",
              transform: `scale(${spriteConfig.scale})`,
              transformOrigin: "center",

              backgroundImage: `url("${spriteConfig.src}")`,
              backgroundRepeat: "no-repeat",

              backgroundPosition: `-${
                spriteColumn * spriteConfig.frameWidth
              }px -${
                spriteRow * spriteConfig.frameHeight
              }px`,

              backgroundSize: `${
                spriteConfig.frameWidth * SPRITE_COLUMNS
              }px ${
                spriteConfig.frameHeight * SPRITE_ROWS
              }px`,
            }}
          />
        ) : (
          <img
            src="/octopus-loading.png"
            alt="Loading"
            draggable={false}
            className="relative h-64 w-64 select-none animate-skuba-float"
          />
        )}
      </div>

      {/* Headline */}
      <h2 className="skuba-display mt-3 text-3xl font-bold tracking-tight text-[#22333B]">
        {config.headline}
      </h2>

      {/* Rotating message */}
      <p className="skuba-display mt-2 h-7 text-[17px] font-semibold text-[#48605F] transition-all duration-300">
        {config.messages[messageIndex]}
      </p>

      {/* Loading bar */}
      <div className="mt-5 h-2 w-80 overflow-hidden rounded-full bg-white/70 shadow-sm">
        <div className="h-full w-1/3 rounded-full bg-[#EE6A4C] animate-skuba-shimmer" />
      </div>

      {/* Slow loading message */}
      {slow && (
        <p className="mt-4 max-w-sm text-sm text-[#48605F]">
          {config.slowMessage}
        </p>
      )}
    </div>
  );
}