import InsightTablePage from "@/components/InsightTablePage"

export default function OpportunityStoresPage() {
  return (
    <InsightTablePage
      endpoint="/insights/distribution_opportunity"
      requiredParams={["chain", "sku", "channel"]}
    />
  )
}