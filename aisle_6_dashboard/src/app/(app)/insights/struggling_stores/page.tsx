import InsightTablePage from "@/components/InsightTablePage"

export default function ChainStrugglingStoresPage() {
  return (
    <InsightTablePage
      endpoint="/insights/struggling_stores"
      requiredParam="chain"
    />
  )
}