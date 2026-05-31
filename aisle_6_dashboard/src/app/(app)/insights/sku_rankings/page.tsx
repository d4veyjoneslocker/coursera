import InsightTablePage from "@/components/InsightTablePage"

export default function SkuRankingsPage() {
  return (
    <InsightTablePage
      endpoint="/email/sku_rankings"
      requiredParams={[]}
    />
  )
}