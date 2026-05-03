"use client"

import { useEffect } from "react"
import posthog from "posthog-js"
import { PostHogProvider } from "@posthog/react"

export default function PHProvider({
  children,
}: {
  children: React.ReactNode
}) {
  useEffect(() => {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,

      // keep this simple for now
      autocapture: true,
      capture_pageview: true,
      capture_pageleave: true,
    })
  }, [])

  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}