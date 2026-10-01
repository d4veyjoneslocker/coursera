"use client"

import { useMemo, useState } from "react"
import Map, {
  Marker,
  NavigationControl,
  Popup,
} from "react-map-gl/mapbox"
import mapboxgl from "mapbox-gl"
import {
  CheckCircle,
  MapPin,
  Package,
  ShoppingCart,
  TrendUp,
  Warehouse,
} from "@phosphor-icons/react"
import { useOrg } from "@/components/OrgContext"


type StoreHealthStatus =
  | "Healthy"
  | "Struggling"
  | "Revived"
  | "New"
  | "Inactive"




export type StoreHealthMapStore = {
  coded_customer: string | null
  chain: string | null

  status: StoreHealthStatus | string | null

  latitude: number | null
  longitude: number | null

  units: number | null
  revenue?: number | null
  reorders: number | null
  vpo: number | null
  skus_selling: number | null

  distributor: string | null
  dc: string | null
}


type StoreHealthMapProps = {
  stores: StoreHealthMapStore[]
}



function formatNumber(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return "—"
  }

  return Math.round(value).toLocaleString()
}


function formatVpo(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return "—"
  }

  return value.toFixed(1)
}


export default function StoreHealthMap({
  stores,
}: StoreHealthMapProps) {
  const { org } = useOrg()

  const statusColors: Record<string, string> = {
    Healthy: org.primary_color ?? "#9A93B0",
    Revived: org.secondary_color ?? "#C58E82",
    New: org.accent_color ?? "#C8795A",
    Struggling: "#D95C5C",
    Inactive: "#A6A3A0",
  }

  const getStatusColor = (status: string | null) => {
    if (!status) {
      return statusColors.Inactive
    }

    return statusColors[status] ?? statusColors.Inactive
  }

  const [hoveredStore, setHoveredStore] =
    useState<StoreHealthMapStore | null>(null)


  const plottedStores = useMemo(() => {
    return stores.filter((store) => {
      const latitude = Number(store.latitude)
      const longitude = Number(store.longitude)

      return (
        Number.isFinite(latitude) &&
        Number.isFinite(longitude)
      )
    })
  }, [stores])


  const bounds = useMemo(() => {
    if (!plottedStores.length) {
      return undefined
    }

    const mapBounds = new mapboxgl.LngLatBounds()

    plottedStores.forEach((store) => {
      mapBounds.extend([
        Number(store.longitude),
        Number(store.latitude),
      ])
    })

    return mapBounds
  }, [plottedStores])


  if (!plottedStores.length) {
    return (
      <div className="flex h-[310px] items-center justify-center rounded-xl border border-[#EEE5D8] bg-[#FFFDF9]">
        <div className="flex flex-col items-center gap-2 text-center">
          <MapPin
            size={28}
            weight="duotone"
            className="text-[#705C4F]"
          />

          <div className="text-sm font-medium text-[#343332]">
            No mapped stores
          </div>

          <div className="max-w-xs text-xs text-[#705C4F]">
            No coordinates are available for the stores in
            the current selection.
          </div>
        </div>
      </div>
    )
  }


  return (
    <div className="overflow-hidden rounded-xl border border-[#EEE5D8] bg-[#FFFDF9]">
      <div className="relative h-[310px]">
        <Map
          mapboxAccessToken={
            process.env.NEXT_PUBLIC_MAPBOX_TOKEN
          }
          mapStyle="mapbox://styles/mapbox/light-v11"
            initialViewState={{
            bounds: [
                [-125, 24], // southwest
                [-66, 50],  // northeast
            ],
            fitBoundsOptions: {
                padding: 30,
            },
            }}
          projection={{ name: "mercator" }}
          style={{
            width: "100%",
            height: "100%",
          }}
        >
          <NavigationControl
            position="top-right"
            showCompass={false}
          />


          {plottedStores.map((store, index) => {
            const color = getStatusColor(store.status)

            return (
              <Marker
                key={`${store.coded_customer}-${index}`}
                latitude={Number(store.latitude)}
                longitude={Number(store.longitude)}
                anchor="center"
              >
                <button
                  type="button"
                  aria-label={
                    store.coded_customer
                      ? `View ${store.coded_customer}`
                      : "View store"
                  }
                  onMouseEnter={() =>
                    setHoveredStore(store)
                  }
                  onMouseLeave={() =>
                    setHoveredStore(null)
                  }
                  onFocus={() =>
                    setHoveredStore(store)
                  }
                  onBlur={() =>
                    setHoveredStore(null)
                  }
                  className="flex h-4 w-4 items-center justify-center rounded-full border-2 border-white shadow-sm transition-transform hover:scale-125 focus:scale-125 focus:outline-none"
                  style={{
                    backgroundColor: color,
                  }}
                />
              </Marker>
            )
          })}


          {hoveredStore &&
            hoveredStore.latitude != null &&
            hoveredStore.longitude != null && (
              <Popup
                latitude={Number(hoveredStore.latitude)}
                longitude={Number(hoveredStore.longitude)}
                anchor="left"
                offset={12}
                closeButton={false}
                closeOnClick={false}
                className="dc-store-popup"
              >
                <div
                  onMouseEnter={() => setHoveredStore(hoveredStore)}
                  onMouseLeave={() => setHoveredStore(null)}
                  className="min-w-[220px] px-1 py-1"
                >
                  <div className="flex items-start gap-2">
                    <div
                      className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                      style={{
                        background: "#F3ECE6",
                        color: getStatusColor(hoveredStore.status),
                      }}
                    >
                      <MapPin size={15} weight="duotone" />
                    </div>

                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-[#343332]">
                        {hoveredStore.coded_customer ?? "Store"}
                      </div>

                      <div className="mt-0.5 text-[11px] text-[#705C4F]">
                        {[
                          hoveredStore.chain,
                          hoveredStore.status,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 space-y-2 border-t border-[#EEE5D8] pt-3">
                    <MetricRow
                      icon={<TrendUp size={15} weight="duotone" />}
                      label="VPO"
                      value={formatVpo(hoveredStore.vpo)}
                    />

                    <MetricRow
                      icon={<ShoppingCart size={15} weight="duotone" />}
                      label="Units"
                      value={formatNumber(hoveredStore.units)}
                    />

                    <MetricRow
                      icon={<Package size={15} weight="duotone" />}
                      label="SKUs Selling"
                      value={formatNumber(hoveredStore.skus_selling)}
                    />

                    <MetricRow
                      icon={<ShoppingCart size={15} weight="duotone" />}
                      label="Reorders"
                      value={formatNumber(hoveredStore.reorders)}
                    />

                    <MetricRow
                      icon={<Warehouse size={15} weight="duotone" />}
                      label="Distributor"
                      value={hoveredStore.distributor ?? "—"}
                    />

                    <MetricRow
                      icon={<MapPin size={15} weight="duotone" />}
                      label="DC"
                      value={hoveredStore.dc ?? "—"}
                    />
                  </div>
                </div>
              </Popup>
            )}
        </Map>
      </div>


      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#EEE5D8] px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {Object.entries(statusColors).map(
            ([status, color]) => (
              <div
                key={status}
                className="flex items-center gap-1.5"
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{
                    backgroundColor: color,
                  }}
                />

                <span className="text-xs text-[#705C4F]">
                  {status}
                </span>
              </div>
            )
          )}
        </div>


        <div className="text-xs text-[#705C4F]">
          {plottedStores.length.toLocaleString()} of{" "}
          {stores.length.toLocaleString()} stores mapped
        </div>
      </div>
    </div>
  )
}


function MetricRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-5">
      <div className="flex items-center gap-2 text-xs text-[#705C4F]">
        {icon}
        <span>{label}</span>
      </div>

      <div className="text-xs font-medium text-[#343332]">
        {value}
      </div>
    </div>
  )
}