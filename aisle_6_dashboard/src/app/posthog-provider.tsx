"use client"

import { useEffect } from "react"
import posthog from "posthog-js"
import { PostHogProvider } from "@posthog/react"
import { supabase } from "@/lib/supabase" // adjust to your actual file path

export default function PHProvider({
  children,
}: {
  children: React.ReactNode
}) {
  useEffect(() => {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST,
      autocapture: true,
      capture_pageview: true,
      capture_pageleave: true,
    })

    let active = true

    // Identify users who are already logged in
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (active && user) {
        posthog.identify(user.id, {
          email: user.email,
        })
      }
    })

    // Identify users when authentication changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" && session?.user) {
        posthog.identify(session.user.id, {
          email: session.user.email,
        })
      }

      if (event === "SIGNED_OUT") {
        posthog.reset()
      }
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  return (
    <PostHogProvider client={posthog}>
      {children}
    </PostHogProvider>
  )
}