import InsightTablePage from "@/components/InsightTablePage"

export default function ChainStrugglingStoresPage() {
  return (
    <InsightTablePage
      endpoint="/insights_new/struggling_stores"
      requiredParam="chain"
    />
  )
}