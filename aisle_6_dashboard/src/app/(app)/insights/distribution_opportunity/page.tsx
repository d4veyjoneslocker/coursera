import InsightTablePage from "@/components/InsightTablePage"

export default function OpportunityStoresPage() {
  return (
    <InsightTablePage
      endpoint="/insights_new/distribution_opportunity"
      requiredParams={["chain", "sku", "channel"]}
    />
  )
}