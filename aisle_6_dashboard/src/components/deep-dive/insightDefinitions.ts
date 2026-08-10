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
}