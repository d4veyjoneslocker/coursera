import InsightTablePage from "@/components/InsightTablePage"

export default function FailureToLaunchStoresPage() {
  return (
    <InsightTablePage
      endpoint="/insights_new/failure_to_launch_new_store_risk/stores"
      requiredParams={["launch_cohort_id"]}
    />
  )
}