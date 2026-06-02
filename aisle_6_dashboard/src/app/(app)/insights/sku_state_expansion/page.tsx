import InsightTablePage from "@/components/InsightTablePage"

export default function NewBuyingStores() {
  return (
    <InsightTablePage
      endpoint="/email/sku_state_expansion/stores"
      requiredParams={["sku"]}
    />
  )
}