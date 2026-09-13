"use client"

import { useState } from "react"
import {
  AlertTriangle,
  ArrowRight,
  Box,
  ChevronRight,
  Clock3,
  MapPin,
  PackageCheck,
  Search,
  Store,
  Truck,
  Warehouse,
} from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"


const theme = {
  primary_color: "#9A93B0",
  secondary_color: "#C58E82",
  accent_color: "#C8795A",
  charcoal: "#343332",
  brown: "#705C4F",
  bg: "#F6F2EA",
  line: "#E5DDD0",
  surface: "#FFFDF9",
  paper: "#FCFAF6",

  greenBg: "#EAF3DE",
  greenText: "#3B6D11",

  redBg: "#FBF1EF",
  redText: "#A06057",

  amberBg: "#FBF0D9",
  amberText: "#9B6A25",
}


// =========================================================
// Mock data
// =========================================================

const dc = {
  distributor: "UNFI",
  code: "HVA",
  name: "Harrisburg, PA",
  status: "Needs attention",

  quantityOnHandCases: 146,
  quantityOnHandUnits: 2192,

  quantityOnPoCases: 98,
  quantityOnPoUnits: 1470,

  weeksOnHand: 2.7,
  weeksWithInbound: 4.5,

  leadTimeDays: 6,
  leadTimeEvents: 41,

  quantityNeededCases: 620,

  activeStores: 42,
  unitsPerWeek: 386,
  casesPerWeek: 48,

  targetWeeks: 8,
}


const skuRows = [
  {
    sku: "VANILLA BEAN",
    displayName: "Vanilla Bean",
    size: "8 oz",
    imageUrl: "/products/vanilla-bean.png",

    onHandCases: 71,
    onPoCases: 30,

    unitsPerWeek: 84,
    casesPerWeek: 10.5,

    weeksOnHand: 6.8,
    weeksWithInbound: 9.6,

    neededCases: 0,
    status: "Healthy",
  },
  {
    sku: "PEANUT BUTTER",
    displayName: "Peanut Butter",
    size: "8 oz",
    imageUrl: "/products/peanut-butter.png",

    onHandCases: 17,
    onPoCases: 30,

    unitsPerWeek: 126,
    casesPerWeek: 15.8,

    weeksOnHand: 1.1,
    weeksWithInbound: 3.0,

    neededCases: 96,
    status: "Needs order",
  },
  {
    sku: "MOCHA JOE",
    displayName: "Mocha Joe",
    size: "8 oz",
    imageUrl: "/products/mocha-joe.png",

    onHandCases: 24,
    onPoCases: 0,

    unitsPerWeek: 72,
    casesPerWeek: 9.0,

    weeksOnHand: 2.7,
    weeksWithInbound: 2.7,

    neededCases: 66,
    status: "Needs order",
  },
  {
    sku: "STRAWBERRY",
    displayName: "Strawberry",
    size: "8 oz",
    imageUrl: "/products/strawberry.png",

    onHandCases: 10,
    onPoCases: 15,

    unitsPerWeek: 64,
    casesPerWeek: 8.0,

    weeksOnHand: 1.3,
    weeksWithInbound: 3.1,

    neededCases: 55,
    status: "Needs order",
  },
]


const storeDots = [
  [46, 47],
  [51, 42],
  [56, 51],
  [42, 56],
  [61, 44],
  [37, 46],
  [48, 61],
  [55, 66],
  [64, 58],
  [31, 57],
  [67, 38],
  [42, 34],
  [58, 31],
  [72, 51],
  [35, 67],
  [63, 72],
  [49, 75],
  [76, 63],
  [29, 39],
]


// =========================================================
// Helpers
// =========================================================

function formatNumber(value: number) {
  return value.toLocaleString("en-US")
}


function MetricCard({
  icon,
  label,
  value,
  unit,
  detail,
  emphasized = false,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  unit?: string
  detail?: string
  emphasized?: boolean
}) {
  return (
    <div
      className="
        group
        rounded-[22px]
        border
        px-4
        py-4
        transition
        duration-200
        hover:-translate-y-[1px]
        hover:shadow-sm
      "
      style={{
        backgroundColor: theme.paper,
        borderColor: theme.line,
      }}
    >
      <div className="flex items-start gap-3">
        <div
          className="
            flex
            h-9
            w-9
            shrink-0
            items-center
            justify-center
            rounded-[12px]
          "
          style={{
            backgroundColor: emphasized
              ? `${theme.accent_color}14`
              : "#F4F1EC",
            color: emphasized
              ? theme.accent_color
              : theme.brown,
          }}
        >
          {icon}
        </div>

        <div className="min-w-0 flex-1">
          <p
            className="
              text-[11px]
              font-medium
              uppercase
              tracking-[0.12em]
            "
            style={{ color: "#9A8A7C" }}
          >
            {label}
          </p>

          <div className="mt-1 flex items-baseline gap-1.5">
            <span
              className="
                text-[29px]
                font-semibold
                leading-none
                tracking-[-0.035em]
              "
              style={{ color: theme.charcoal }}
            >
              {value}
            </span>

            {unit && (
              <span
                className="text-[13px]"
                style={{ color: theme.brown }}
              >
                {unit}
              </span>
            )}
          </div>

          {detail && (
            <p
              className="mt-1.5 text-[12px]"
              style={{ color: "#9A8A7C" }}
            >
              {detail}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}


function StatusPill({
  status,
}: {
  status: string
}) {
  const healthy = status === "Healthy"

  return (
    <span
      className="
        inline-flex
        items-center
        rounded-full
        px-3
        py-1.5
        text-[12px]
        font-medium
      "
      style={{
        backgroundColor: healthy
          ? theme.greenBg
          : theme.redBg,
        color: healthy
          ? theme.greenText
          : theme.redText,
      }}
    >
      {status}
    </span>
  )
}


function ProductImage({
  src,
  name,
}: {
  src: string
  name: string
}) {
  return (
    <div
      className="
        flex
        h-12
        w-12
        shrink-0
        items-center
        justify-center
        overflow-hidden
        rounded-[14px]
        border
      "
      style={{
        backgroundColor: "#F7F2E9",
        borderColor: theme.line,
      }}
    >
      <img
        src={src}
        alt={name}
        className="h-full w-full object-contain p-1"
        onError={(event) => {
          event.currentTarget.style.display = "none"
        }}
      />
    </div>
  )
}


// =========================================================
// Page
// =========================================================

export default function DistributionCenterDetailPage() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "inventory" | "stores"
  >("inventory")

  return (
    <main
      className="min-h-screen px-6 py-8"
      style={{ backgroundColor: theme.bg }}
    >
      <div className="mx-auto max-w-[1500px]">

        {/* =====================================================
            Breadcrumb
        ===================================================== */}

        <div
          className="
            mb-5
            flex
            items-center
            gap-2
            text-[12px]
          "
          style={{ color: "#9A8A7C" }}
        >
          <span>Inventory</span>
          <ChevronRight size={13} />
          <span>Distribution Centers</span>
          <ChevronRight size={13} />

          <span
            className="font-medium"
            style={{ color: theme.charcoal }}
          >
            {dc.distributor} · {dc.code}
          </span>
        </div>


        {/* =====================================================
            Main DC Card
        ===================================================== */}

        <Card
          className="overflow-hidden rounded-[28px] shadow-sm"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <CardContent className="p-0">

            <div className="grid lg:grid-cols-[0.92fr_1.08fr]">

              {/* =================================================
                  LEFT
              ================================================= */}

              <section
                className="
                  border-b
                  p-6
                  lg:border-b-0
                  lg:border-r
                  lg:p-7
                "
                style={{ borderColor: theme.line }}
              >

                {/* Header */}

                <div className="mb-6 flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h1
                        className="
                          text-[34px]
                          font-semibold
                          leading-none
                          tracking-[-0.04em]
                        "
                        style={{ color: theme.charcoal }}
                      >
                        {dc.distributor} · {dc.code}
                      </h1>

                      <span
                        className="
                          inline-flex
                          items-center
                          gap-2
                          rounded-full
                          px-3
                          py-1.5
                          text-[12px]
                          font-medium
                        "
                        style={{
                          backgroundColor: theme.redBg,
                          color: theme.redText,
                        }}
                      >
                        <span
                          className="h-1.5 w-1.5 rounded-full"
                          style={{
                            backgroundColor: theme.redText,
                          }}
                        />

                        {dc.status}
                      </span>
                    </div>

                    <div
                      className="
                        mt-2
                        flex
                        items-center
                        gap-1.5
                        text-[13px]
                      "
                      style={{ color: theme.brown }}
                    >
                      <MapPin size={14} />
                      {dc.name} Distribution Center
                    </div>
                  </div>
                </div>


                {/* Metrics */}

                <div className="grid grid-cols-2 gap-3">
                  <MetricCard
                    icon={<Warehouse size={18} />}
                    label="Quantity on hand"
                    value={formatNumber(
                      dc.quantityOnHandCases
                    )}
                    unit="cases"
                    detail={`${formatNumber(
                      dc.quantityOnHandUnits
                    )} units`}
                  />

                  <MetricCard
                    icon={<Truck size={18} />}
                    label="On purchase order"
                    value={formatNumber(
                      dc.quantityOnPoCases
                    )}
                    unit="cases"
                    detail={`${formatNumber(
                      dc.quantityOnPoUnits
                    )} units`}
                  />

                  <MetricCard
                    icon={<PackageCheck size={18} />}
                    label="Weeks on hand"
                    value={dc.weeksOnHand}
                    unit="weeks"
                    detail={`vs. ${dc.targetWeeks} week target`}
                  />

                  <MetricCard
                    icon={<Box size={18} />}
                    label="WOH + inbound"
                    value={dc.weeksWithInbound}
                    unit="weeks"
                    detail="Includes open POs"
                  />

                  <MetricCard
                    icon={<Clock3 size={18} />}
                    label="Est. lead time"
                    value={dc.leadTimeDays}
                    unit="days"
                    detail={`Based on ${dc.leadTimeEvents} observed deliveries`}
                  />

                  <MetricCard
                    icon={<AlertTriangle size={18} />}
                    label="Quantity needed"
                    value={formatNumber(
                      dc.quantityNeededCases
                    )}
                    unit="cases"
                    detail={`To reach ${dc.targetWeeks} weeks`}
                    emphasized
                  />
                </div>


                {/* Recommendation */}

                <div
                  className="
                    mt-4
                    rounded-[22px]
                    border
                    px-5
                    py-4
                  "
                  style={{
                    backgroundColor: "#FBF1EF",
                    borderColor: "#F0DDD8",
                  }}
                >
                  <div className="flex gap-3">
                    <div
                      className="
                        mt-0.5
                        flex
                        h-8
                        w-8
                        shrink-0
                        items-center
                        justify-center
                        rounded-full
                      "
                      style={{
                        backgroundColor: "#F5DDD7",
                        color: theme.redText,
                      }}
                    >
                      <AlertTriangle size={16} />
                    </div>

                    <div>
                      <p
                        className="text-[16px] font-semibold"
                        style={{ color: theme.redText }}
                      >
                        {formatNumber(
                          dc.quantityNeededCases
                        )}{" "}
                        cases needed
                      </p>

                      <p
                        className="
                          mt-1
                          max-w-xl
                          text-[13px]
                          leading-5
                        "
                        style={{ color: theme.brown }}
                      >
                        Current inventory and open POs
                        are projected below your{" "}
                        {dc.targetWeeks}-week target after
                        accounting for this DC&apos;s{" "}
                        {dc.leadTimeDays}-day delivery time.
                      </p>
                    </div>
                  </div>
                </div>
              </section>


              {/* =================================================
                  RIGHT / MAP
              ================================================= */}

              <section className="p-6 lg:p-7">

                <div
                  className="
                    relative
                    min-h-[390px]
                    overflow-hidden
                    rounded-[24px]
                    border
                  "
                  style={{
                    borderColor: theme.line,
                    background:
                      "linear-gradient(145deg, #EEF1E9 0%, #E8EEE7 46%, #EDE8DD 100%)",
                  }}
                >
                  {/* fake geography */}

                  <div
                    className="
                      absolute
                      left-[18%]
                      top-[15%]
                      h-[70%]
                      w-[68%]
                      rotate-[-8deg]
                      rounded-[42%]
                      border
                    "
                    style={{
                      borderColor: "#D7DDD2",
                    }}
                  />

                  <div
                    className="
                      absolute
                      left-[32%]
                      top-[12%]
                      h-[80%]
                      w-px
                      rotate-[26deg]
                    "
                    style={{
                      backgroundColor: "#D7DDD2",
                    }}
                  />

                  <div
                    className="
                      absolute
                      left-[58%]
                      top-[5%]
                      h-[90%]
                      w-px
                      rotate-[-32deg]
                    "
                    style={{
                      backgroundColor: "#D7DDD2",
                    }}
                  />

                  {/* map label */}

                  <div
                    className="
                      absolute
                      left-5
                      top-5
                      rounded-full
                      border
                      px-3
                      py-1.5
                      text-[11px]
                      font-medium
                    "
                    style={{
                      backgroundColor: "#FFFDF9E8",
                      borderColor: theme.line,
                      color: theme.brown,
                    }}
                  >
                    All retailers
                  </div>


                  {/* stores */}

                  {storeDots.map(([left, top], index) => (
                    <div
                      key={index}
                      className="
                        absolute
                        h-2.5
                        w-2.5
                        rounded-full
                        shadow-sm
                      "
                      style={{
                        left: `${left}%`,
                        top: `${top}%`,
                        backgroundColor: "#48605F",
                      }}
                    />
                  ))}


                  {/* DC */}

                  <div
                    className="
                      absolute
                      left-[50%]
                      top-[51%]
                      flex
                      h-12
                      w-12
                      -translate-x-1/2
                      -translate-y-1/2
                      items-center
                      justify-center
                      rounded-full
                      border-[5px]
                      shadow-lg
                    "
                    style={{
                      backgroundColor: "#FFFDF9",
                      borderColor: "#48605F",
                    }}
                  >
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{
                        backgroundColor: theme.accent_color,
                      }}
                    />
                  </div>


                  {/* location label */}

                  <div
                    className="
                      absolute
                      left-[53%]
                      top-[57%]
                      text-[12px]
                      font-semibold
                    "
                    style={{ color: theme.charcoal }}
                  >
                    HVA
                  </div>


                  {/* Map Stats */}

                  <div
                    className="
                      absolute
                      bottom-4
                      left-4
                      right-4
                      grid
                      grid-cols-3
                      divide-x
                      rounded-[18px]
                      border
                      px-2
                      py-3
                      shadow-sm
                    "
                    style={{
                      backgroundColor: "#FFFDF9F2",
                      borderColor: theme.line,
                    }}
                  >
                    <MapStat
                      icon={<Store size={17} />}
                      value={dc.activeStores}
                      label="Active stores"
                    />

                    <MapStat
                      icon={<PackageCheck size={17} />}
                      value={dc.unitsPerWeek}
                      label="Units / week"
                    />

                    <MapStat
                      icon={<Box size={17} />}
                      value={dc.casesPerWeek}
                      label="Cases / week"
                    />
                  </div>
                </div>


                {/* Map actions */}

                <div className="mt-3 flex justify-end gap-2">
                  <button
                    className="
                      rounded-full
                      border
                      px-4
                      py-2
                      text-[12px]
                      font-medium
                      transition
                      hover:bg-[#F7F2EA]
                    "
                    style={{
                      borderColor: theme.line,
                      color: theme.brown,
                    }}
                  >
                    View store list
                  </button>

                  <button
                    className="
                      inline-flex
                      items-center
                      gap-2
                      rounded-full
                      px-4
                      py-2
                      text-[12px]
                      font-medium
                      text-white
                      transition
                      hover:opacity-90
                    "
                    style={{
                      backgroundColor: theme.accent_color,
                    }}
                  >
                    Add stores
                    <ArrowRight size={14} />
                  </button>
                </div>
              </section>
            </div>
          </CardContent>
        </Card>


        {/* =====================================================
            Detail Area
        ===================================================== */}

        <Card
          className="
            mt-5
            overflow-hidden
            rounded-[28px]
            shadow-sm
          "
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.line,
          }}
        >
          <CardContent className="p-0">

            {/* Tabs */}

            <div
              className="
                flex
                items-center
                justify-between
                gap-4
                border-b
                px-6
              "
              style={{ borderColor: theme.line }}
            >
              <div className="flex items-center gap-8">

                {[
                  ["overview", "Overview"],
                  ["inventory", "Inventory Snapshot"],
                  ["stores", "Stores"],
                ].map(([key, label]) => {
                  const selected =
                    activeTab === key

                  return (
                    <button
                      key={key}
                      onClick={() =>
                        setActiveTab(
                          key as
                            | "overview"
                            | "inventory"
                            | "stores"
                        )
                      }
                      className="
                        relative
                        py-5
                        text-[13px]
                        font-medium
                      "
                      style={{
                        color: selected
                          ? theme.charcoal
                          : "#9A8A7C",
                      }}
                    >
                      {label}

                      {selected && (
                        <span
                          className="
                            absolute
                            bottom-0
                            left-0
                            h-[2px]
                            w-full
                            rounded-full
                          "
                          style={{
                            backgroundColor:
                              theme.accent_color,
                          }}
                        />
                      )}
                    </button>
                  )
                })}
              </div>


              {activeTab === "inventory" && (
                <div
                  className="
                    hidden
                    items-center
                    gap-2
                    rounded-full
                    border
                    px-3
                    py-2
                    md:flex
                  "
                  style={{
                    borderColor: theme.line,
                    backgroundColor: theme.paper,
                  }}
                >
                  <Search
                    size={14}
                    color="#9A8A7C"
                  />

                  <input
                    placeholder="Search SKUs"
                    className="
                      w-36
                      bg-transparent
                      text-[12px]
                      outline-none
                    "
                    style={{
                      color: theme.charcoal,
                    }}
                  />
                </div>
              )}
            </div>


            {/* Inventory Snapshot */}

            {activeTab === "inventory" && (
              <div className="px-6 pb-5 pt-3">

                {/* column headers */}

                <div
                  className="
                    grid
                    grid-cols-[2.2fr_.75fr_.75fr_.85fr_.85fr_.65fr_.75fr_.7fr_.9fr_24px]
                    items-center
                    gap-4
                    px-3
                    py-3
                    text-[10px]
                    font-medium
                    uppercase
                    tracking-[0.1em]
                  "
                  style={{ color: "#9A8A7C" }}
                >
                  <span>Product</span>
                  <span>On hand</span>
                  <span>On PO</span>
                  <span>Units / wk</span>
                  <span>Cases / wk</span>
                  <span>WOH</span>
                  <span>WOH + PO</span>
                  <span>Needed</span>
                  <span>Status</span>
                  <span />
                </div>


                {/* rows */}

                <div className="space-y-2">
                  {skuRows.map((row) => (
                    <button
                      key={row.sku}
                      className="
                        grid
                        w-full
                        grid-cols-[2.2fr_.75fr_.75fr_.85fr_.85fr_.65fr_.75fr_.7fr_.9fr_24px]
                        items-center
                        gap-4
                        rounded-[18px]
                        border
                        px-3
                        py-3
                        text-left
                        transition
                        duration-150
                        hover:-translate-y-[1px]
                        hover:shadow-sm
                      "
                      style={{
                        backgroundColor: theme.paper,
                        borderColor: theme.line,
                      }}
                    >

                      {/* Product */}

                      <div className="flex min-w-0 items-center gap-3">
                        <ProductImage
                          src={row.imageUrl}
                          name={row.displayName}
                        />

                        <div className="min-w-0">
                          <p
                            className="
                              truncate
                              text-[14px]
                              font-semibold
                            "
                            style={{
                              color: theme.charcoal,
                            }}
                          >
                            {row.displayName}
                          </p>

                          <p
                            className="mt-0.5 text-[11px]"
                            style={{
                              color: "#9A8A7C",
                            }}
                          >
                            {row.size}
                          </p>
                        </div>
                      </div>


                      <SnapshotValue
                        value={row.onHandCases}
                        suffix="cs"
                      />

                      <SnapshotValue
                        value={row.onPoCases}
                        suffix="cs"
                      />

                      <SnapshotValue
                        value={row.unitsPerWeek}
                      />

                      <SnapshotValue
                        value={row.casesPerWeek}
                      />

                      <SnapshotValue
                        value={row.weeksOnHand}
                      />

                      <SnapshotValue
                        value={row.weeksWithInbound}
                      />

                      <div>
                        <span
                          className="text-[14px] font-semibold"
                          style={{
                            color:
                              row.neededCases > 0
                                ? theme.redText
                                : theme.greenText,
                          }}
                        >
                          {row.neededCases}
                        </span>

                        <span
                          className="ml-1 text-[10px]"
                          style={{
                            color: "#9A8A7C",
                          }}
                        >
                          cs
                        </span>
                      </div>

                      <StatusPill
                        status={row.status}
                      />

                      <ChevronRight
                        size={16}
                        color="#9A8A7C"
                      />
                    </button>
                  ))}
                </div>
              </div>
            )}


            {activeTab === "overview" && (
              <div
                className="
                  px-8
                  py-14
                  text-center
                  text-sm
                "
                style={{ color: theme.brown }}
              >
                DC overview content goes here.
              </div>
            )}


            {activeTab === "stores" && (
              <div
                className="
                  px-8
                  py-14
                  text-center
                  text-sm
                "
                style={{ color: theme.brown }}
              >
                Store-level demand detail goes here.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  )
}


// =========================================================
// Small components
// =========================================================

function MapStat({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode
  value: number
  label: string
}) {
  return (
    <div className="flex items-center justify-center gap-3 px-4">
      <div
        className="
          flex
          h-8
          w-8
          items-center
          justify-center
          rounded-[10px]
        "
        style={{
          backgroundColor: "#F4F1EC",
          color: theme.brown,
        }}
      >
        {icon}
      </div>

      <div>
        <p
          className="
            text-[20px]
            font-semibold
            leading-none
            tracking-[-0.03em]
          "
          style={{ color: theme.charcoal }}
        >
          {value}
        </p>

        <p
          className="mt-1 text-[10px]"
          style={{ color: "#9A8A7C" }}
        >
          {label}
        </p>
      </div>
    </div>
  )
}


function SnapshotValue({
  value,
  suffix,
}: {
  value: number
  suffix?: string
}) {
  return (
    <div>
      <span
        className="text-[13px] font-medium"
        style={{ color: theme.charcoal }}
      >
        {value}
      </span>

      {suffix && (
        <span
          className="ml-1 text-[10px]"
          style={{ color: "#9A8A7C" }}
        >
          {suffix}
        </span>
      )}
    </div>
  )
}