"use client"

type GrowthDriver = {
  total_change?: number | null
  distribution_impact?: number | null
  velocity_impact?: number | null
  distribution_share?: number | null
  velocity_share?: number | null
  primary_driver?: string | null
}

type Story = {
  story_type: string
  direction: "positive" | "negative" | "mixed"

  scope_type: string

  scope: {
    chain?: string
    state?: string
    sku?: string
  }

  signal_types: string[]

  diagnostics?: {
    units_growth_driver?: GrowthDriver
  }

  strength: number
}

type OrganizedStories = {
  overall: Story[]
  sku: Story[]
  retailer: Story[]
  state: Story[]
}

type Props = {
  stories: OrganizedStories
}

function formatScope(story: Story) {
  const parts: string[] = []

  if (story.scope.chain) {
    parts.push(story.scope.chain)
  }

  if (story.scope.state) {
    parts.push(story.scope.state)
  }

  if (story.scope.sku) {
    parts.push(story.scope.sku)
  }

  return parts.length
    ? parts.join(" · ")
    : "Overall Business"
}

function formatStoryType(type: string) {
  const labels: Record<string, string> = {
    distribution_and_velocity_growth:
      "Distribution + Velocity Growth",

    distribution_led_growth_with_velocity:
      "Growth Led by Distribution, Supported by Velocity",

    velocity_led_growth_with_distribution:
      "Growth Led by Velocity, Supported by Distribution",

    distribution_growth_offset_by_velocity_pressure:
      "Distribution Growth, Offset by Velocity Pressure",

    velocity_growth_offset_by_distribution:
      "Velocity Growth, Offset by Distribution Loss",

    distribution_led_growth:
      "Distribution-Led Growth",

    velocity_led_growth:
      "Velocity-Led Growth",

    distribution_and_velocity_decline:
      "Distribution + Velocity Decline",

    distribution_led_decline_with_velocity_pressure:
      "Decline Led by Distribution Loss + Velocity Pressure",

    velocity_led_decline_with_distribution_loss:
      "Decline Led by Velocity + Distribution Loss",

    distribution_decline_offset_by_velocity_growth:
      "Distribution Decline, Offset by Velocity Growth",

    velocity_decline_offset_by_distribution_growth:
      "Velocity Decline, Offset by Distribution Growth",

    distribution_led_decline:
      "Distribution-Led Decline",

    velocity_led_decline:
      "Velocity-Led Decline",
  }

  return (
    labels[type] ??
    type
      .replaceAll("_", " ")
      .replace(/\b\w/g, (c) => c.toUpperCase())
  )
}

function formatPercent(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—"
  }

  return `${value >= 0 ? "+" : ""}${(
    value * 100
  ).toFixed(0)}%`
}

function formatNumber(
  value?: number | null
) {
  if (
    value === null ||
    value === undefined
  ) {
    return "—"
  }

  return value.toLocaleString(
    undefined,
    {
      maximumFractionDigits: 0,
    }
  )
}

function StoryCard({
  story,
}: {
  story: Story
}) {
  const driver =
    story.diagnostics
      ?.units_growth_driver

  return (
    <div className="rounded-2xl border bg-white p-5 shadow-sm">

      {/* Header */}

      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-1 text-xs font-semibold ${
                story.direction === "positive"
                  ? "bg-green-100 text-green-700"
                  : story.direction === "negative"
                  ? "bg-red-100 text-red-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {story.direction.toUpperCase()}
            </span>

            <span className="text-xs uppercase tracking-wide text-neutral-400">
              {story.scope_type.replaceAll(
                "_",
                " "
              )}
            </span>
          </div>

          <h3 className="text-base font-semibold text-neutral-900">
            {formatStoryType(
              story.story_type
            )}
          </h3>

          <p className="mt-1 text-sm text-neutral-500">
            {formatScope(story)}
          </p>
        </div>

        <div className="text-right">
          <div className="text-lg font-semibold text-neutral-900">
            {story.strength.toFixed(2)}
          </div>

          <div className="text-xs uppercase tracking-wide text-neutral-400">
            Strength
          </div>
        </div>
      </div>


      {/* Diagnostic */}

      {driver && (
        <div className="mt-5 rounded-xl bg-neutral-50 p-4">

          <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">
            Why
          </div>

          <div className="grid grid-cols-2 gap-3">

            <div>
              <div className="text-xs text-neutral-400">
                Primary Driver
              </div>

              <div className="text-sm font-semibold capitalize">
                {driver.primary_driver ?? "—"}
              </div>
            </div>


            <div>
              <div className="text-xs text-neutral-400">
                Unit Change
              </div>

              <div className="text-sm font-semibold">
                {formatNumber(
                  driver.total_change
                )}
              </div>
            </div>


            <div>
              <div className="text-xs text-neutral-400">
                Distribution Impact
              </div>

              <div className="text-sm font-semibold">
                {formatNumber(
                  driver.distribution_impact
                )}
              </div>
            </div>


            <div>
              <div className="text-xs text-neutral-400">
                Velocity Impact
              </div>

              <div className="text-sm font-semibold">
                {formatNumber(
                  driver.velocity_impact
                )}
              </div>
            </div>


            <div>
              <div className="text-xs text-neutral-400">
                Distribution Share
              </div>

              <div className="text-sm font-semibold">
                {formatPercent(
                  driver.distribution_share
                )}
              </div>
            </div>


            <div>
              <div className="text-xs text-neutral-400">
                Velocity Share
              </div>

              <div className="text-sm font-semibold">
                {formatPercent(
                  driver.velocity_share
                )}
              </div>
            </div>

          </div>
        </div>
      )}


      {/* Signals underneath */}

      {story.signal_types?.length > 0 && (
        <div className="mt-4">

          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-400">
            Signals Combined
          </div>

          <div className="flex flex-wrap gap-2">
            {story.signal_types.map(
              (signal) => (
                <span
                  key={signal}
                  className="rounded-full bg-neutral-100 px-2 py-1 text-xs text-neutral-600"
                >
                  {signal.replaceAll(
                    "_",
                    " "
                  )}
                </span>
              )
            )}
          </div>

        </div>
      )}

    </div>
  )
}

function StorySection({
  title,
  stories,
}: {
  title: string
  stories: Story[]
}) {
  if (!stories?.length) {
    return null
  }

  return (
    <section className="space-y-4">

      <div>
        <h3 className="text-lg font-semibold text-neutral-900">
          {title}
        </h3>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {stories.map((story, index) => (
          <StoryCard
            key={`${story.scope_type}-${formatScope(story)}-${index}`}
            story={story}
          />
        ))}
      </div>

    </section>
  )
}

export default function BusinessStories({
  stories,
}: Props) {
  if (
    !stories ||
    (
      !stories.overall?.length &&
      !stories.sku?.length &&
      !stories.retailer?.length &&
      !stories.state?.length
    )
  ) {
    return (
      <div className="rounded-2xl border bg-white p-5">
        <p className="text-sm text-neutral-500">
          No business stories detected.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-10">

      <StorySection
        title="Overall Business"
        stories={stories.overall ?? []}
      />

      <StorySection
        title="SKU Portfolio"
        stories={stories.sku ?? []}
      />

      <StorySection
        title="Top Retailers"
        stories={stories.retailer ?? []}
      />

      <StorySection
        title="Top States"
        stories={stories.state ?? []}
      />

    </div>
  )
}