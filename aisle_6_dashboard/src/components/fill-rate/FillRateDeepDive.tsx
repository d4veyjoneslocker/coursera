"use client"

import { useState } from "react"

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  PackageCheck,
} from "lucide-react"

// ============================================================
// COLORS
// ============================================================

const COLORS = {
  surface: "#FCFAF6",
  surfaceAlt: "#FFFDF9",
  line: "#EEE5D8",
  brown: "#705C4F",
  muted: "#8A8179",
  charcoal: "#343332",
  danger: "#B85F4A",
  dangerBg: "#FBF1EF",
  warning: "#9A7428",
  warningBg: "#FFF8E8",
  success: "#55735E",
  successBg: "#F1F8F3",
}

// ============================================================
// TYPES
// ============================================================

type Tone = "danger" | "warning" | "success" | "neutral"

type MonthlyPoint = {
  month: string
  value: number | null
}

type InventoryRow = {
  dc: string
  woh: number
  daysToOos: string
  poLabel: string
  poDetail?: string
  status: string
  tone: Tone
}

type SkuStory = {
  id: string
  sku: string

  headline: string
  description: string

  salesChange: number

  orderHeadline: string
  orderPill: string
  orderPillTone: Tone
  orderData: MonthlyPoint[]
  orderFinding: React.ReactNode

  fillHeadline: string
  fillPill: string
  fillPillTone: Tone
  fillData: MonthlyPoint[]
  fillFinding: React.ReactNode

  sequence: {
    order: string
    fill: string
    sales: string
  }

  finding: React.ReactNode

  inventoryTitle: string
  inventorySubtitle: string
  inventoryStatus: string
  inventoryTone: Tone
  inventoryRows: InventoryRow[]
}

type RetailerStory = {
  id: string
  retailer: string
  period: string
  skus: SkuStory[]
}

// ============================================================
// DATA
//
// IMPORTANT:
// Apr–Aug Order VPO below has already been divided by 8.
// September is used as-is because the transform was fixed by then.
// ============================================================

const STORIES: RetailerStory[] = [
  // ==========================================================
  // FRESH THYME
  // ==========================================================

  {
    id: "fresh-thyme",
    retailer: "Fresh Thyme",
    period: "Last 3 months",

    skus: [
      // --------------------------------------------------------
      // PEANUT BUTTER
      // --------------------------------------------------------

      {
        id: "peanut-butter",
        sku: "Peanut Butter",

        headline:
          "Fresh Thyme slowed sharply as fulfillment broke down",

        description:
          "Peanut Butter sales velocity had already been trending lower before a severe August fulfillment breakdown pushed sales to zero. September shows improvement, but fulfillment and inventory remain under pressure.",

        salesChange: -63,

        orderHeadline: "0.67 → 2.46 → 2.96",
        orderPill: "Orders surged",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 2.17 },
          { month: "May", value: 1.51 },
          { month: "Jun", value: 0.9 },
          { month: "Jul", value: 0.67 },
          { month: "Aug", value: 2.46 },
          { month: "Sep", value: 2.96 },
        ],

        orderFinding: (
          <>
            <strong>August:</strong> Order velocity jumped nearly 4×
            from July and remained elevated in September.
          </>
        ),

        fillHeadline: "91% → 0% → 39%",
        fillPill: "Major breakdown",
        fillPillTone: "danger",

        fillData: [
          { month: "Apr", value: 100 },
          { month: "May", value: 100 },
          { month: "Jun", value: 100 },
          { month: "Jul", value: 91 },
          { month: "Aug", value: 0 },
          { month: "Sep", value: 39 },
        ],

        fillFinding: (
          <>
            <strong>September:</strong> Fill rate improved from zero,
            but at 39% remained far below prior service levels.
          </>
        ),

        sequence: {
          order: "Surged",
          fill: "Fell to 0%",
          sales: "Fell to zero",
        },

        finding: (
          <>
            Peanut Butter was already slowing before August. Ordering
            then increased sharply while fulfillment collapsed. Sales
            improved in September as product began shipping again, but{" "}
            <strong>
              fill rate remained weak and BLO inventory is still tight.
            </strong>
          </>
        ),

        inventoryTitle: "BLO remains tight on Peanut Butter",
        inventorySubtitle:
          "Fresh Thyme · Peanut Butter · KeHE BLO",

        inventoryStatus: "Needs attention",
        inventoryTone: "warning",

        inventoryRows: [
          {
            dc: "BLO",
            woh: 2.2,
            daysToOos: "~15 days",
            poLabel: "No active PO",
            poDetail: "Projected order expected",
            status: "High",
            tone: "warning",
          },
        ],
      },

      // --------------------------------------------------------
      // STRAWBERRY
      // --------------------------------------------------------

      {
        id: "strawberry",
        sku: "Strawberry",

        headline:
          "Fresh Thyme Strawberry was hit by a sharp August fulfillment gap",

        description:
          "Sales had already been slowing before August. Ordering then increased sharply while fill rate fell to just 8%, adding fulfillment pressure to an already softer sales trend.",

        salesChange: -60,

        orderHeadline: "0.61 → 2.09 → 1.22",
        orderPill: "August spike",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 2.29 },
          { month: "May", value: 1.45 },
          { month: "Jun", value: 0.99 },
          { month: "Jul", value: 0.61 },
          { month: "Aug", value: 2.09 },
          { month: "Sep", value: 1.22 },
        ],

        orderFinding: (
          <>
            <strong>August:</strong> Order velocity increased more
            than 3× from July before moderating to 1.22 in September.
          </>
        ),

        fillHeadline: "100% → 8% → 100%",
        fillPill: "August breakdown",
        fillPillTone: "danger",

        fillData: [
          { month: "Apr", value: 100 },
          { month: "May", value: 100 },
          { month: "Jun", value: 100 },
          { month: "Jul", value: 100 },
          { month: "Aug", value: 8 },
          { month: "Sep", value: 100 },
        ],

        fillFinding: (
          <>
            <strong>September:</strong> Reported fill rate returned to
            100% after the August disruption.
          </>
        ),

        sequence: {
          order: "Spiked",
          fill: "Fell to 8%",
          sales: "Fell sharply",
        },

        finding: (
          <>
            Strawberry sales were already trending lower, so
            fulfillment does not explain the full decline. But the
            August disruption added significant pressure just as
            retailer ordering increased.{" "}
            <strong>
              Fulfillment normalized in September, while BLO remains
              below three weeks of inventory.
            </strong>
          </>
        ),

        inventoryTitle: "BLO remains tight on Strawberry",
        inventorySubtitle:
          "Fresh Thyme · Strawberry · KeHE BLO",

        inventoryStatus: "Needs attention",
        inventoryTone: "warning",

        inventoryRows: [
          {
            dc: "BLO",
            woh: 2.4,
            daysToOos: "~17 days",
            poLabel: "No active PO",
            poDetail: "Projected order expected",
            status: "High",
            tone: "warning",
          },
        ],
      },

      // --------------------------------------------------------
      // VANILLA BEAN
      // --------------------------------------------------------

      {
        id: "vanilla-bean",
        sku: "Vanilla Bean",

        headline:
          "Fresh Thyme Vanilla Bean lost fulfillment entirely in August",

        description:
          "Ordering increased sharply in August while fill rate fell to zero. Sales also fell to zero before both sales and fulfillment improved in September.",

        salesChange: -63,

        orderHeadline: "0.78 → 2.38 → 1.10",
        orderPill: "August spike",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 2.14 },
          { month: "May", value: 1.88 },
          { month: "Jun", value: 0.75 },
          { month: "Jul", value: 0.78 },
          { month: "Aug", value: 2.38 },
          { month: "Sep", value: 1.1 },
        ],

        orderFinding: (
          <>
            <strong>August:</strong> Order velocity increased more
            than 3× from July before falling back to 1.10 in September.
          </>
        ),

        fillHeadline: "100% → 0% → 100%",
        fillPill: "August breakdown",
        fillPillTone: "danger",

        fillData: [
          { month: "Apr", value: 100 },
          { month: "May", value: 100 },
          { month: "Jun", value: 100 },
          { month: "Jul", value: 100 },
          { month: "Aug", value: 0 },
          { month: "Sep", value: 100 },
        ],

        fillFinding: (
          <>
            <strong>September:</strong> Reported fill rate returned to
            100% after no reported August demand was fulfilled.
          </>
        ),

        sequence: {
          order: "Spiked",
          fill: "Fell to 0%",
          sales: "Fell to zero",
        },

        finding: (
          <>
            Vanilla Bean had reported retailer demand in August, but
            none of it was fulfilled. Service returned to 100% in
            September, while{" "}
            <strong>
              BLO remains at only 1.9 weeks of inventory.
            </strong>
          </>
        ),

        inventoryTitle:
          "Vanilla Bean has the tightest BLO inventory position",

        inventorySubtitle:
          "Fresh Thyme · Vanilla Bean · KeHE BLO",

        inventoryStatus: "Critical",
        inventoryTone: "danger",

        inventoryRows: [
          {
            dc: "BLO",
            woh: 1.9,
            daysToOos: "~13 days",
            poLabel: "No active PO",
            poDetail: "Projected order expected",
            status: "Critical",
            tone: "danger",
          },
        ],
      },
    ],
  },

  // ==========================================================
  // SPROUTS
  // ==========================================================

  {
    id: "sprouts",
    retailer: "Sprouts",
    period: "Last 3 months",

    skus: [
      // --------------------------------------------------------
      // MOCHA JOE
      // --------------------------------------------------------

      {
        id: "mocha-joe",
        sku: "Mocha Joe",

        headline:
          "Sprouts Mocha Joe faced a sharp August fulfillment disruption",

        description:
          "Sales velocity has weakened over the last three months. August stands out because ordering increased while fill rate fell sharply, before service recovered in September.",

        salesChange: -41,

        orderHeadline: "0.97 → 1.64 → 0.63",
        orderPill: "August spike",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 1.57 },
          { month: "May", value: 1.53 },
          { month: "Jun", value: 0.97 },
          { month: "Jul", value: 0.97 },
          { month: "Aug", value: 1.64 },
          { month: "Sep", value: 0.63 },
        ],

        orderFinding: (
          <>
            <strong>August:</strong> Order velocity rose to 1.64
            before falling to 0.63 in September.
          </>
        ),

        fillHeadline: "93% → 55% → 97%",
        fillPill: "August disruption",
        fillPillTone: "danger",

        fillData: [
          { month: "Apr", value: 99 },
          { month: "May", value: 99 },
          { month: "Jun", value: 97 },
          { month: "Jul", value: 93 },
          { month: "Aug", value: 55 },
          { month: "Sep", value: 97 },
        ],

        fillFinding: (
          <>
            <strong>September:</strong> Fill rate returned to 97%
            after falling to 55% in August.
          </>
        ),

        sequence: {
          order: "Rose in Aug",
          fill: "Fell to 55%",
          sales: "Remained weak",
        },

        finding: (
          <>
            Mocha Joe sales were already softening, but August added a
            clear fulfillment problem: ordering increased while fill
            rate fell to 55%. Service recovered in September, although{" "}
            <strong>
              order velocity finished the month at only 0.63.
            </strong>
          </>
        ),

        inventoryTitle:
          "Mocha Joe inventory is covered, but MIA should be monitored",

        inventorySubtitle:
          "Sprouts · Mocha Joe · KeHE",

        inventoryStatus: "Monitor",
        inventoryTone: "neutral",

        inventoryRows: [
          {
            dc: "MIA",
            woh: 8.0,
            daysToOos: "~56 days",
            poLabel: "Projected order",
            poDetail: "Expected to cover future gap",
            status: "Monitor",
            tone: "neutral",
          },
          {
            dc: "DGV",
            woh: 18.8,
            daysToOos: "~131 days",
            poLabel: "No PO needed",
            poDetail: "Inventory healthy",
            status: "Healthy",
            tone: "success",
          },
        ],
      },

      // --------------------------------------------------------
      // PEANUT BUTTER
      // --------------------------------------------------------

      {
        id: "peanut-butter",
        sku: "Peanut Butter",

        headline:
          "Sprouts Peanut Butter sales continued to soften",

        description:
          "Peanut Butter sales velocity is down versus the prior three months. Fulfillment weakened modestly in July and August, while ordering also trended lower into September.",

        salesChange: -36,

        orderHeadline: "1.49 → 1.28 → 1.04",
        orderPill: "Ordering softened",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 2.08 },
          { month: "May", value: 2.26 },
          { month: "Jun", value: 1.16 },
          { month: "Jul", value: 1.49 },
          { month: "Aug", value: 1.28 },
          { month: "Sep", value: 1.04 },
        ],

        orderFinding: (
          <>
            <strong>September:</strong> Order velocity declined to
            1.04 after reaching 2.26 in May.
          </>
        ),

        fillHeadline: "85% → 84% → 91%",
        fillPill: "Below prior levels",
        fillPillTone: "warning",

        fillData: [
          { month: "Apr", value: 99 },
          { month: "May", value: 82 },
          { month: "Jun", value: 100 },
          { month: "Jul", value: 85 },
          { month: "Aug", value: 84 },
          { month: "Sep", value: 91 },
        ],

        fillFinding: (
          <>
            Fill rate remained below earlier levels through July and
            August, then improved to 91% in September.
          </>
        ),

        sequence: {
          order: "Trending lower",
          fill: "Stayed below 100%",
          sales: "Down 36%",
        },

        finding: (
          <>
            Peanut Butter does not show the same dramatic fulfillment
            collapse as other Sprouts SKUs. Instead,{" "}
            <strong>
              both ordering and sales have softened while fill rate has
              remained somewhat inconsistent.
            </strong>{" "}
            Current MIA inventory is healthy.
          </>
        ),

        inventoryTitle:
          "Current Peanut Butter inventory appears healthy",

        inventorySubtitle:
          "Sprouts · Peanut Butter · KeHE MIA",

        inventoryStatus: "Healthy",
        inventoryTone: "success",

        inventoryRows: [
          {
            dc: "MIA",
            woh: 9.5,
            daysToOos: "~67 days",
            poLabel: "No PO needed",
            poDetail: "Inventory remains above floor",
            status: "Healthy",
            tone: "success",
          },
        ],
      },

      // --------------------------------------------------------
      // VANILLA BEAN
      // --------------------------------------------------------

      {
        id: "vanilla-bean",
        sku: "Vanilla Bean",

        headline:
          "Sprouts Vanilla Bean demand held up while fulfillment deteriorated",

        description:
          "Ordering increased sharply in August while fill rate deteriorated. Sales remained relatively stable through August before weakening in September.",

        salesChange: -37,

        orderHeadline: "1.72 → 3.02 → 1.48",
        orderPill: "August surge",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 2.04 },
          { month: "May", value: 2.16 },
          { month: "Jun", value: 1.3 },
          { month: "Jul", value: 1.72 },
          { month: "Aug", value: 3.02 },
          { month: "Sep", value: 1.48 },
        ],

        orderFinding: (
          <>
            <strong>August:</strong> Order velocity rose 76% from July
            while fulfillment deteriorated sharply.
          </>
        ),

        fillHeadline: "69% → 39% → 70%",
        fillPill: "Fulfillment pressure",
        fillPillTone: "danger",

        fillData: [
          { month: "Apr", value: 99 },
          { month: "May", value: 92 },
          { month: "Jun", value: 99 },
          { month: "Jul", value: 69 },
          { month: "Aug", value: 39 },
          { month: "Sep", value: 70 },
        ],

        fillFinding: (
          <>
            <strong>September:</strong> Fill rate improved to 70%,
            but remained well below the near-100% levels seen earlier
            in the year.
          </>
        ),

        sequence: {
          order: "Rose 76%",
          fill: "Fell to 39%",
          sales: "Stayed pressured",
        },

        finding: (
          <>
            This does not look like a simple demand problem. Retailer
            ordering increased materially in August while fulfillment
            deteriorated. Service improved in September, but{" "}
            <strong>
              EMD is currently out of stock and DFW remains relatively
              tight.
            </strong>
          </>
        ),

        inventoryTitle:
          "Two DCs still need attention for Vanilla Bean",

        inventorySubtitle:
          "Sprouts · Vanilla Bean · KeHE",

        inventoryStatus: "Needs attention",
        inventoryTone: "warning",

        inventoryRows: [
          {
            dc: "EMD",
            woh: 0,
            daysToOos: "Out of stock",
            poLabel: "105-case PO",
            poDetail: "Active PO outstanding",
            status: "Critical",
            tone: "danger",
          },
          {
            dc: "DFW",
            woh: 3.1,
            daysToOos: "~22 days",
            poLabel: "No active PO",
            poDetail: "Inventory near floor",
            status: "Action",
            tone: "warning",
          },
          {
            dc: "MIA",
            woh: 5.9,
            daysToOos: "~41 days",
            poLabel: "Projected order",
            poDetail: "Expected to cover future gap",
            status: "Monitor",
            tone: "neutral",
          },
          {
            dc: "DGV",
            woh: 15.6,
            daysToOos: "~109 days",
            poLabel: "No PO needed",
            poDetail: "Inventory healthy",
            status: "Healthy",
            tone: "success",
          },
          {
            dc: "AUR",
            woh: 21.5,
            daysToOos: "~150 days",
            poLabel: "No PO needed",
            poDetail: "Inventory healthy",
            status: "Healthy",
            tone: "success",
          },
        ],
      },
    ],
  },

  // ==========================================================
  // KEY FOOD
  // ==========================================================

  {
    id: "key-food",
    retailer: "Key Food",
    period: "Last 3 months",

    skus: [
      // --------------------------------------------------------
      // MOCHA JOE
      // --------------------------------------------------------

      {
        id: "mocha-joe",
        sku: "Mocha Joe",

        headline:
          "Key Food Mocha Joe weakened further as fill rate deteriorated",

        description:
          "Sales and ordering remain at low levels, while fill rate deteriorated in both August and September. September is the weakest fulfillment month in the current six-month view.",

        salesChange: -58,

        orderHeadline: "0.33 → 1.25 → 0.75",
        orderPill: "Ordering remains low",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 3.0 },
          { month: "May", value: 1.0 },
          { month: "Jun", value: 1.6 },
          { month: "Jul", value: 0.33 },
          { month: "Aug", value: 1.25 },
          { month: "Sep", value: 0.75 },
        ],

        orderFinding: (
          <>
            Ordering increased from a very low July level in August,
            then finished September at only 0.75 VPO.
          </>
        ),

        fillHeadline: "100% → 80% → 33%",
        fillPill: "Deteriorating",
        fillPillTone: "danger",

        fillData: [
          { month: "Apr", value: 100 },
          { month: "May", value: 100 },
          { month: "Jun", value: 100 },
          { month: "Jul", value: 100 },
          { month: "Aug", value: 80 },
          { month: "Sep", value: 33 },
        ],

        fillFinding: (
          <>
            <strong>September:</strong> Fill rate fell further to 33%,
            the lowest level in the six-month view.
          </>
        ),

        sequence: {
          order: "Remained low",
          fill: "Fell to 33%",
          sales: "Remained weak",
        },

        finding: (
          <>
            Mocha Joe has both a demand and fulfillment concern:
            ordering and sales are low, while fulfillment has now
            deteriorated materially.{" "}
            <strong>
              EMD inventory is also down to roughly one week on hand.
            </strong>
          </>
        ),

        inventoryTitle:
          "EMD has roughly one week of Mocha Joe inventory",

        inventorySubtitle:
          "Key Food · Mocha Joe · KeHE EMD",

        inventoryStatus: "Needs attention",
        inventoryTone: "danger",

        inventoryRows: [
          {
            dc: "EMD",
            woh: 1.1,
            daysToOos: "~7 days",
            poLabel: "45-case PO",
            poDetail: "Active PO outstanding",
            status: "Critical",
            tone: "danger",
          },
        ],
      },

      // --------------------------------------------------------
      // PEANUT BUTTER
      // --------------------------------------------------------

      {
        id: "peanut-butter",
        sku: "Peanut Butter",

        headline:
          "Key Food Peanut Butter remains weak with worsening fulfillment",

        description:
          "Ordering and sales remain at low levels. After no May order, ordering resumed but stayed limited, while fill rate deteriorated in both August and September.",

        salesChange: -68,

        orderHeadline: "0.29 → 0.75 → 0.50",
        orderPill: "Ordering remains low",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 2.67 },
          { month: "May", value: 0 },
          { month: "Jun", value: 1.33 },
          { month: "Jul", value: 0.29 },
          { month: "Aug", value: 0.75 },
          { month: "Sep", value: 0.5 },
        ],

        orderFinding: (
          <>
            Ordering increased from a very low July level in August,
            but remained just 0.50 VPO in September.
          </>
        ),

        fillHeadline: "100% → 67% → 50%",
        fillPill: "Deteriorating",
        fillPillTone: "danger",

        fillData: [
          { month: "Apr", value: 100 },
          { month: "May", value: null },
          { month: "Jun", value: 100 },
          { month: "Jul", value: 100 },
          { month: "Aug", value: 67 },
          { month: "Sep", value: 50 },
        ],

        fillFinding: (
          <>
            <strong>May:</strong> No order was reported, so fill rate
            is not applicable. Fulfillment then fell to 67% in August
            and 50% in September.
          </>
        ),

        sequence: {
          order: "Remained low",
          fill: "Fell to 50%",
          sales: "Remained weak",
        },

        finding: (
          <>
            Peanut Butter's weakness cannot be attributed to
            fulfillment alone because ordering and sales were already
            low. However,{" "}
            <strong>
              worsening fill rate is now adding additional pressure,
            </strong>{" "}
            and EMD inventory is below three weeks on hand.
          </>
        ),

        inventoryTitle:
          "EMD Peanut Butter inventory is below three weeks",

        inventorySubtitle:
          "Key Food · Peanut Butter · KeHE EMD",

        inventoryStatus: "Needs attention",
        inventoryTone: "warning",

        inventoryRows: [
          {
            dc: "EMD",
            woh: 2.5,
            daysToOos: "~17 days",
            poLabel: "60-case PO",
            poDetail: "Active PO outstanding",
            status: "High",
            tone: "warning",
          },
        ],
      },

      // --------------------------------------------------------
      // VANILLA BEAN
      // --------------------------------------------------------

      {
        id: "vanilla-bean",
        sku: "Vanilla Bean",

        headline:
          "Key Food Vanilla Bean remains weak despite normalized fulfillment",

        description:
          "Ordering and sales remain low. Fill rate fell to 60% in August and returned to 100% in September, but the current EMD inventory position creates an immediate operational risk.",

        salesChange: -64,

        orderHeadline: "0.29 → 1.25 → 0.50",
        orderPill: "Ordering remains low",
        orderPillTone: "warning",

        orderData: [
          { month: "Apr", value: 2.67 },
          { month: "May", value: 0 },
          { month: "Jun", value: 2.0 },
          { month: "Jul", value: 0.29 },
          { month: "Aug", value: 1.25 },
          { month: "Sep", value: 0.5 },
        ],

        orderFinding: (
          <>
            Ordering increased from a very low July level in August,
            then fell back to only 0.50 VPO in September.
          </>
        ),

        fillHeadline: "100% → 60% → 100%",
        fillPill: "August disruption",
        fillPillTone: "warning",

        fillData: [
          { month: "Apr", value: 100 },
          { month: "May", value: null },
          { month: "Jun", value: 100 },
          { month: "Jul", value: 100 },
          { month: "Aug", value: 60 },
          { month: "Sep", value: 100 },
        ],

        fillFinding: (
          <>
            <strong>May:</strong> No order was reported, so fill rate
            is not applicable. Reported fill rate returned to 100% in
            September after the August disruption.
          </>
        ),

        sequence: {
          order: "Remained low",
          fill: "Recovered to 100%",
          sales: "Remained weak",
        },

        finding: (
          <>
            Vanilla Bean's sales weakness predates the August
            fulfillment issue, and September ordering remains low even
            after fill rate normalized. The immediate concern is now
            operational:{" "}
            <strong>
              EMD is at 0.0 weeks on hand with an outstanding PO.
            </strong>
          </>
        ),

        inventoryTitle:
          "EMD is currently out of stock on Vanilla Bean",

        inventorySubtitle:
          "Key Food · Vanilla Bean · KeHE EMD",

        inventoryStatus: "Critical",
        inventoryTone: "danger",

        inventoryRows: [
          {
            dc: "EMD",
            woh: 0,
            daysToOos: "Out of stock",
            poLabel: "105-case PO",
            poDetail: "Active PO outstanding",
            status: "Critical",
            tone: "danger",
          },
        ],
      },
    ],
  },
]

// ============================================================
// SMALL COMPONENTS
// ============================================================

function SectionLabel({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <p
      className="text-[10px] font-semibold uppercase tracking-[0.16em]"
      style={{ color: COLORS.muted }}
    >
      {children}
    </p>
  )
}

function StatusPill({
  children,
  tone,
}: {
  children: React.ReactNode
  tone: Tone
}) {
  const styles = {
    danger: {
      backgroundColor: COLORS.dangerBg,
      color: COLORS.danger,
      borderColor: "#F0C8BE",
    },
    warning: {
      backgroundColor: COLORS.warningBg,
      color: COLORS.warning,
      borderColor: "#E8D5B5",
    },
    success: {
      backgroundColor: COLORS.successBg,
      color: COLORS.success,
      borderColor: "#CFE2D6",
    },
    neutral: {
      backgroundColor: "#F4F1EC",
      color: COLORS.brown,
      borderColor: COLORS.line,
    },
  }

  return (
    <span
      className="inline-flex whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-semibold"
      style={styles[tone]}
    >
      {children}
    </span>
  )
}

// ============================================================
// RETAILER TABS
// ============================================================

function RetailerTabs({
  selected,
  onSelect,
}: {
  selected: string
  onSelect: (id: string) => void
}) {
  return (
    <div>
      <SectionLabel>Retailer</SectionLabel>

      <div className="mt-2 flex flex-wrap gap-2">
        {STORIES.map((story) => {
          const active = selected === story.id

          return (
            <button
              key={story.id}
              type="button"
              onClick={() => onSelect(story.id)}
              className="rounded-full border px-4 py-2 text-[12px] font-semibold transition-all"
              style={{
                backgroundColor: active
                  ? COLORS.charcoal
                  : COLORS.surfaceAlt,
                borderColor: active
                  ? COLORS.charcoal
                  : COLORS.line,
                color: active
                  ? COLORS.surfaceAlt
                  : COLORS.brown,
              }}
            >
              {story.retailer}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================
// SKU TABS
// ============================================================

function SkuTabs({
  skus,
  selected,
  onSelect,
}: {
  skus: SkuStory[]
  selected: string
  onSelect: (id: string) => void
}) {
  return (
    <div>
      <SectionLabel>Product</SectionLabel>

      <div
        className="mt-2 inline-flex flex-wrap gap-1 rounded-xl border p-1"
        style={{
          backgroundColor: "#F4EFE7",
          borderColor: COLORS.line,
        }}
      >
        {skus.map((sku) => {
          const active = selected === sku.id

          return (
            <button
              key={sku.id}
              type="button"
              onClick={() => onSelect(sku.id)}
              className="rounded-lg px-4 py-2 text-[12px] font-semibold transition-all"
              style={{
                backgroundColor: active
                  ? COLORS.surfaceAlt
                  : "transparent",
                color: active
                  ? COLORS.charcoal
                  : COLORS.muted,
                boxShadow: active
                  ? "0 1px 3px rgba(52,51,50,0.08)"
                  : "none",
              }}
            >
              {sku.sku}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================
// TOOLTIP
// ============================================================

function ChartTooltip({
  active,
  payload,
  label,
  suffix = "",
  decimals = 2,
}: any) {
  if (!active || !payload?.length) return null

  const value = payload[0]?.value

  if (value == null) return null

  return (
    <div
      className="rounded-xl border px-3 py-2 shadow-md"
      style={{
        backgroundColor: COLORS.surfaceAlt,
        borderColor: COLORS.line,
      }}
    >
      <p
        className="text-[11px] font-medium"
        style={{ color: COLORS.muted }}
      >
        {label}
      </p>

      <p
        className="mt-0.5 text-[14px] font-semibold"
        style={{ color: COLORS.charcoal }}
      >
        {Number(value).toFixed(decimals)}
        {suffix}
      </p>
    </div>
  )
}

// ============================================================
// CHART
// ============================================================

function MetricChart({
  type,
  sku,
  headline,
  pill,
  pillTone,
  data,
  finding,
}: {
  type: "order" | "fill"
  sku: string
  headline: string
  pill: string
  pillTone: Tone
  data: MonthlyPoint[]
  finding: React.ReactNode
}) {
  const isOrder = type === "order"
  const stroke = isOrder ? COLORS.brown : COLORS.danger

  return (
    <div
      className="rounded-[24px] border p-6"
      style={{
        backgroundColor: COLORS.surfaceAlt,
        borderColor: COLORS.line,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <SectionLabel>
            {isOrder ? "Order Velocity" : "Fill Rate"}
          </SectionLabel>

          <p
            className="mt-1 text-[11px] font-semibold"
            style={{ color: COLORS.brown }}
          >
            {sku}
          </p>
        </div>

        <StatusPill tone={pillTone}>
          <span className="inline-flex items-center gap-1">
            {pillTone === "success" ? (
              <ArrowUpRight size={12} />
            ) : pillTone === "danger" ? (
              <ArrowDownRight size={12} />
            ) : (
              <AlertTriangle size={11} />
            )}

            {pill}
          </span>
        </StatusPill>
      </div>

      <p
        className="mt-3 text-[28px] font-semibold tracking-[-0.04em]"
        style={{ color: COLORS.charcoal }}
      >
        {headline}
      </p>

      <p
        className="mt-1 text-[12px]"
        style={{ color: COLORS.muted }}
      >
        {isOrder
          ? "Units ordered per store per week"
          : "Share of ordered product shipped"}
      </p>

      <div className="mt-5 h-[205px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{
              top: 8,
              right: 10,
              bottom: 12,
              left: -18,
            }}
          >
            <CartesianGrid
              vertical={false}
              stroke={COLORS.line}
              strokeDasharray="3 3"
            />

            <ReferenceLine
              x="Aug"
              stroke={COLORS.danger}
              strokeOpacity={0.28}
              strokeDasharray="3 3"
            />

            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{
                fill: COLORS.muted,
                fontSize: 11,
              }}
              dy={8}
            />

            <YAxis
              axisLine={false}
              tickLine={false}
              domain={isOrder ? [0, "auto"] : [0, 100]}
              ticks={
                isOrder
                  ? undefined
                  : [0, 25, 50, 75, 100]
              }
              tickFormatter={
                isOrder
                  ? undefined
                  : (value) => `${value}%`
              }
              tick={{
                fill: COLORS.muted,
                fontSize: 10,
              }}
            />

            <Tooltip
              cursor={{
                stroke: COLORS.line,
                strokeWidth: 1,
              }}
              content={
                <ChartTooltip
                  suffix={isOrder ? "" : "%"}
                  decimals={isOrder ? 2 : 0}
                />
              }
            />

            <Line
              type="linear"
              dataKey="value"
              connectNulls={false}
              stroke={stroke}
              strokeWidth={2.5}
              dot={{
                r: 4,
                fill: COLORS.surfaceAlt,
                stroke,
                strokeWidth: 2,
              }}
              activeDot={{
                r: 5,
                fill: stroke,
                stroke: COLORS.surfaceAlt,
                strokeWidth: 2,
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div
        className="mt-3 border-t pt-4"
        style={{ borderColor: COLORS.line }}
      >
        <p
          className="text-[13px] leading-6"
          style={{ color: COLORS.brown }}
        >
          {finding}
        </p>
      </div>
    </div>
  )
}

// ============================================================
// WHAT SKUba FOUND
// ============================================================

function FindingStep({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: Tone
}) {
  const color =
    tone === "danger"
      ? COLORS.danger
      : tone === "success"
        ? COLORS.success
        : tone === "warning"
          ? COLORS.warning
          : COLORS.charcoal

  return (
    <div className="min-w-0 flex-1">
      <p
        className="text-[10px] font-semibold uppercase tracking-[0.14em]"
        style={{ color: COLORS.muted }}
      >
        {label}
      </p>

      <p
        className="mt-1 text-[19px] font-semibold tracking-[-0.025em]"
        style={{ color }}
      >
        {value}
      </p>
    </div>
  )
}

function WhatSkubaFound({
  story,
}: {
  story: SkuStory
}) {
  return (
    <div
      className="rounded-[24px] border px-6 py-6 md:px-7"
      style={{
        backgroundColor: "#F8F4EC",
        borderColor: COLORS.line,
      }}
    >
      <div className="flex items-start gap-4">
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
          style={{
            backgroundColor: COLORS.surfaceAlt,
            color: COLORS.brown,
          }}
        >
          <AlertTriangle size={17} strokeWidth={2} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <SectionLabel>What SKUba Found</SectionLabel>

            <span style={{ color: COLORS.line }}>·</span>

            <span
              className="text-[10px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: COLORS.brown }}
            >
              {story.sku}
            </span>
          </div>

          <div className="mt-5 flex flex-col gap-4 md:flex-row md:items-center">
            <FindingStep
              label="Orders"
              value={story.sequence.order}
              tone="warning"
            />

            <ArrowRight
              className="hidden shrink-0 md:block"
              size={18}
              color={COLORS.muted}
            />

            <FindingStep
              label="Fill rate"
              value={story.sequence.fill}
              tone="danger"
            />

            <ArrowRight
              className="hidden shrink-0 md:block"
              size={18}
              color={COLORS.muted}
            />

            <FindingStep
              label="Sales"
              value={story.sequence.sales}
              tone="danger"
            />
          </div>

          <div
            className="mt-5 border-t pt-4"
            style={{ borderColor: COLORS.line }}
          >
            <p
              className="max-w-5xl text-[14px] leading-6"
              style={{ color: COLORS.charcoal }}
            >
              {story.finding}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// INVENTORY
// ============================================================

function InventoryRisk({
  retailer,
  story,
}: {
  retailer: string
  story: SkuStory
}) {
  return (
    <div
      className="overflow-hidden rounded-[24px] border"
      style={{
        backgroundColor: COLORS.surfaceAlt,
        borderColor: COLORS.line,
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4 px-6 py-5">
        <div>
          <div className="flex items-center gap-2">
            <AlertTriangle
              size={15}
              strokeWidth={2}
              color={
                story.inventoryTone === "danger"
                  ? COLORS.danger
                  : story.inventoryTone === "success"
                    ? COLORS.success
                    : COLORS.warning
              }
            />

            <SectionLabel>Current Inventory Position</SectionLabel>
          </div>

          <h3
            className="mt-2 text-[19px] font-semibold tracking-[-0.025em]"
            style={{ color: COLORS.charcoal }}
          >
            {story.inventoryTitle}
          </h3>

          <p
            className="mt-1 text-[12px]"
            style={{ color: COLORS.muted }}
          >
            {story.inventorySubtitle}
          </p>
        </div>

        <StatusPill tone={story.inventoryTone}>
          {story.inventoryStatus}
        </StatusPill>
      </div>

      <div style={{ borderTop: `1px solid ${COLORS.line}` }}>
        {story.inventoryRows.map((row, index) => {
          const healthy = row.tone === "success"

          return (
            <div
              key={`${story.id}-${row.dc}`}
              className="grid gap-4 px-6 py-4 md:grid-cols-[minmax(0,1.2fr)_0.7fr_0.8fr_1.2fr_auto] md:items-center"
              style={{
                borderTop:
                  index === 0
                    ? undefined
                    : `1px solid ${COLORS.line}`,
              }}
            >
              <div>
                <p
                  className="text-[14px] font-semibold"
                  style={{ color: COLORS.charcoal }}
                >
                  {row.dc}
                </p>

                <p
                  className="mt-0.5 text-[11px]"
                  style={{ color: COLORS.muted }}
                >
                  {retailer} · {story.sku}
                </p>
              </div>

              <div>
                <p
                  className="text-[10px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: COLORS.muted }}
                >
                  Weeks on hand
                </p>

                <p
                  className="mt-1 text-[15px] font-semibold"
                  style={{
                    color:
                      row.tone === "danger"
                        ? COLORS.danger
                        : COLORS.charcoal,
                  }}
                >
                  {row.woh.toFixed(1)}
                </p>
              </div>

              <div>
                <p
                  className="text-[10px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: COLORS.muted }}
                >
                  Projected OOS
                </p>

                <p
                  className="mt-1 text-[14px] font-semibold"
                  style={{
                    color:
                      row.tone === "danger"
                        ? COLORS.danger
                        : COLORS.charcoal,
                  }}
                >
                  {row.daysToOos}
                </p>
              </div>

              <div>
                <p
                  className="text-[10px] font-semibold uppercase tracking-[0.12em]"
                  style={{ color: COLORS.muted }}
                >
                  PO Coverage
                </p>

                <div className="mt-1 flex items-center gap-2">
                  {healthy ? (
                    <CheckCircle2
                      size={14}
                      color={COLORS.success}
                    />
                  ) : (
                    <PackageCheck
                      size={14}
                      color={
                        row.tone === "danger"
                          ? COLORS.danger
                          : COLORS.warning
                      }
                    />
                  )}

                  <div>
                    <p
                      className="text-[13px] font-medium"
                      style={{ color: COLORS.charcoal }}
                    >
                      {row.poLabel}
                    </p>

                    {row.poDetail && (
                      <p
                        className="text-[10px]"
                        style={{ color: COLORS.muted }}
                      >
                        {row.poDetail}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <StatusPill tone={row.tone}>
                {row.status}
              </StatusPill>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================
// DEEP DIVE
// ============================================================

function StoryDeepDive({
  retailer,
  period,
  story,
  skuSelector,
}: {
  retailer: string
  period: string
  story: SkuStory
  skuSelector: React.ReactNode
}) {
  return (
    <section
      className="rounded-[32px] border px-6 py-7 shadow-[0_14px_34px_rgba(52,51,50,0.05)] md:px-8 md:py-8"
      style={{
        backgroundColor: COLORS.surface,
        borderColor: COLORS.line,
      }}
    >
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="text-[11px] font-semibold uppercase tracking-[0.18em]"
            style={{ color: COLORS.brown }}
          >
            {retailer}
          </span>

          <span style={{ color: COLORS.line }}>·</span>

          <span
            className="text-[11px] font-medium uppercase tracking-[0.18em]"
            style={{ color: COLORS.muted }}
          >
            Deep Dive
          </span>

          <span style={{ color: COLORS.line }}>·</span>

          <span
            className="text-[11px] font-medium uppercase tracking-[0.18em]"
            style={{ color: COLORS.muted }}
          >
            {period}
          </span>
        </div>

        <h2
          className="mt-3 max-w-4xl text-[29px] font-semibold leading-[1.15] tracking-[-0.04em] md:text-[34px]"
          style={{ color: COLORS.charcoal }}
        >
          {story.headline}
        </h2>

        <p
          className="mt-3 max-w-3xl text-[14px] leading-6"
          style={{ color: COLORS.brown }}
        >
          {story.description}
        </p>
      </div>

      {/* PRODUCT SELECTOR */}

      <div className="mt-6">{skuSelector}</div>

      {/* BUSINESS OUTCOME */}

      <div
        className="mt-6 flex flex-col gap-3 border-y py-6 sm:flex-row sm:items-end sm:gap-7"
        style={{ borderColor: COLORS.line }}
      >
        <div>
          <div className="flex items-center gap-2">
            <SectionLabel>Business Outcome</SectionLabel>

            <span style={{ color: COLORS.line }}>·</span>

            <span
              className="text-[10px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: COLORS.brown }}
            >
              {story.sku}
            </span>
          </div>

          <p
            className="mt-2 text-[56px] font-semibold leading-none tracking-[-0.06em]"
            style={{
              color:
                story.salesChange < 0
                  ? COLORS.danger
                  : COLORS.success,
            }}
          >
            {story.salesChange > 0 ? "+" : ""}
            {story.salesChange}%
          </p>
        </div>

        <div className="pb-1">
          <p
            className="text-[17px] font-semibold"
            style={{ color: COLORS.charcoal }}
          >
            Sales velocity
          </p>

          <p
            className="mt-1 text-[12px]"
            style={{ color: COLORS.muted }}
          >
            {story.sku} · L3M vs prior 3M
          </p>
        </div>
      </div>

      {/* CHARTS */}

      <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-2">
        <MetricChart
          type="order"
          sku={story.sku}
          headline={story.orderHeadline}
          pill={story.orderPill}
          pillTone={story.orderPillTone}
          data={story.orderData}
          finding={story.orderFinding}
        />

        <MetricChart
          type="fill"
          sku={story.sku}
          headline={story.fillHeadline}
          pill={story.fillPill}
          pillTone={story.fillPillTone}
          data={story.fillData}
          finding={story.fillFinding}
        />
      </div>

      {/* FINDING */}

      <div className="mt-5">
        <WhatSkubaFound story={story} />
      </div>

      {/* INVENTORY */}

      <div className="mt-5">
        <InventoryRisk
          retailer={retailer}
          story={story}
        />
      </div>
    </section>
  )
}

// ============================================================
// MAIN
// ============================================================

export default function FillRateDeepDive() {
  const [selectedRetailer, setSelectedRetailer] =
    useState("fresh-thyme")

  const retailer =
    STORIES.find(
      (story) => story.id === selectedRetailer,
    ) ?? STORIES[0]

  const [selectedSku, setSelectedSku] =
    useState(retailer.skus[0].id)

  const skuStory =
    retailer.skus.find(
      (sku) => sku.id === selectedSku,
    ) ?? retailer.skus[0]

  function handleRetailerChange(retailerId: string) {
    const nextRetailer =
      STORIES.find(
        (story) => story.id === retailerId,
      ) ?? STORIES[0]

    setSelectedRetailer(retailerId)
    setSelectedSku(nextRetailer.skus[0].id)
  }

  return (
    <div>
      {/* RETAILER SELECTOR */}

      <div
        className="mb-5 flex flex-col gap-4 rounded-[20px] border p-4 md:flex-row md:items-end md:justify-between"
        style={{
          backgroundColor: COLORS.surfaceAlt,
          borderColor: COLORS.line,
        }}
      >
        <RetailerTabs
          selected={selectedRetailer}
          onSelect={handleRetailerChange}
        />

        <p
          className="hidden text-[11px] md:block"
          style={{ color: COLORS.muted }}
        >
          Select a retailer, then choose a product to diagnose.
        </p>
      </div>

      {/* DEEP DIVE */}

      <StoryDeepDive
        retailer={retailer.retailer}
        period={retailer.period}
        story={skuStory}
        skuSelector={
          <SkuTabs
            skus={retailer.skus}
            selected={skuStory.id}
            onSelect={setSelectedSku}
          />
        }
      />
    </div>
  )
}