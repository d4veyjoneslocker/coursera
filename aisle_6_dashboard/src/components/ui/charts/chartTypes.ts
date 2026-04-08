export type MetricRow = {
  month_year: string
  value: number
}

export type PieRow = {
  name: string
  value: number
}

export type KpiItem = {
  key: string
  title: string
  value: number
  sideValue?: number | null
  sideLabel?: string | null
}