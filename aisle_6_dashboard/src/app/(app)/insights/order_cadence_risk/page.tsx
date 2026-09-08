import InsightTablePage from "@/components/InsightTablePage"

export default function OrderCadenceRiskStoresPage() {
  return (
    <InsightTablePage
      endpoint="/insights_new/order_cadence_risk/stores"
      requiredParams={[]}
    />
  )
}