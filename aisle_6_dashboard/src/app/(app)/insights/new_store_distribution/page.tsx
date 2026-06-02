import InsightTablePage from "@/components/InsightTablePage"

export default function NewBuyingStores() {
  return (
    <InsightTablePage
      endpoint="/email/new_store_distribution/stores"
      requiredParams={["sku"]}
    />
  )
}