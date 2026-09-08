import InsightTablePage from "@/components/InsightTablePage"

export default function DropoffSkuRiskStoresPage() {
  return (
    <InsightTablePage
      endpoint="/insights_new/dropoff_sku_risk/stores"
      requiredParams={[]}
    />
  )
}