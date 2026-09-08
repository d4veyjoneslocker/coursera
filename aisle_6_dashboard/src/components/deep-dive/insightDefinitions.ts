export const insightDefinitions = {
  distribution_opportunity: {
    whatItIs:
      "Stores that currently buy your brand but don't carry this SKU.",

    howItsCalculated:
      "SKUba identifies stores buying at least one of your products, then finds stores without recent purchases of this SKU. Annualized opportunity assumes those stores perform at the SKU's current velocity.",

    whyItMatters:
      "These stores already buy your brand, making them a more actionable distribution opportunity than completely new accounts.",
  },

  overperforming_channel_momentum: {
    whatItIs:
      "A channel generating more unit volume than its share of buying stores would suggest.",

    howItsCalculated:
      "SKUba compares the channel's share of recent units with its share of recent buying stores. It also checks whether velocity is above the business average and whether reorder activity remains healthy.",

    whyItMatters:
      "A channel that produces disproportionately strong volume from its current footprint may be a good place to prioritize expansion, retailer storytelling, or account focus.",
  },

  chain_struggling: {
    whatItIs:
        "A retailer where a disproportionately high share of stores are showing signs of weakening reorder activity.",

    howItsCalculated:
        "SKUba compares the share of struggling stores within each retailer against the overall business average. Retailers are flagged when struggling stores are meaningfully more concentrated than normal, with reorder behavior used as additional context.",

    whyItMatters:
        "A concentrated group of struggling stores can signal retailer-specific execution or retention issues that may require attention before more distribution is lost.",
    },

    failure_to_launch_new_store_risk: {
        whatItIs:
            "Recent launch placements that received an initial shipment but have not reordered within the expected launch window.",

        howItsCalculated:
            "SKUba identifies new chain-store-SKU placements, then checks whether they reorder during the first two full months after launch. Cohorts are flagged when a meaningful share of placements still have not reordered.",

        whyItMatters:
            "Early reorder behavior is one of the clearest signals that a new placement is sticking. Placements that fail to reorder may need retailer follow-up, execution support, or a closer look at the initial load-in.",
        },
    dropoff_sku_risk: {
      whatItIs:
        "A SKU that has stopped shipping to stores that are still actively buying your brand.",

      howItsCalculated:
        "SKUba identifies stores that purchased the SKU in the prior three full months but have not purchased it in the latest three full months. Stores are only flagged if they are still purchasing other products from your brand.",

      whyItMatters:
        "Because these stores are still buying your brand, the drop-off is more likely to be SKU-specific rather than a lost account. It can point to authorization, availability, setup, or displacement issues worth investigating.",
    },

    order_cadence_risk: {
      whatItIs:
        "Historically consistent stores that have missed an expected replenishment.",

      howItsCalculated:
        "SKUba identifies stores that purchased in at least three of the prior four months but did not receive a shipment in the latest full month or the current month.",

      whyItMatters:
        "A sudden break in an otherwise consistent ordering pattern can be an early signal of an inventory gap, distribution disruption, reset, or other issue before the store is fully lost.",
    },
}