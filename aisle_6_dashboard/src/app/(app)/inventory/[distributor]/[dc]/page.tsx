"use client"

import { useParams } from "next/navigation"
import DcDetailContent from "@/components/inventory/DcDetailContent"

export default function DistributionCenterDetailPage() {
  const params = useParams()

  const distributor = String(
    params.distributor ?? ""
  )

  const dcCode = String(
    params.dc ?? ""
  )

  return (
    <DcDetailContent
      distributor={distributor}
      dcCode={dcCode}
    />
  )
}