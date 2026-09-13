"use client"

import { useMemo, useState } from "react"
import Map, {
  Marker,
  NavigationControl,
  Popup,
} from "react-map-gl"
import mapboxgl from "mapbox-gl"
import { Store, Warehouse } from "lucide-react"

import "mapbox-gl/dist/mapbox-gl.css"


type MapStore = {
  coded_customer: string | null
  chain: string | null
  channel?: string | null
  state?: string | null
  latitude?: number | null
  longitude?: number | null
}


type DcStoreMapProps = {
  dcCode: string
  dcName?: string | null

  dcLatitude?: number | null
  dcLongitude?: number | null

  stores: MapStore[]
}


const theme = {
  coral: "#EE6A4C",
  secondary: "#C58E82",
  charcoal: "#343332",
  brown: "#705C4F",
  line: "#EEE5D8",
  surface: "#FFFDF9",
}


export default function DcStoreMap({
  dcCode,
  dcName,
  dcLatitude,
  dcLongitude,
  stores,
}: DcStoreMapProps) {
  const [hoveredStore, setHoveredStore] =
    useState<MapStore | null>(null)


  const plottedStores = useMemo(() => {
    return stores.filter(
      (
        store
      ): store is MapStore & {
        latitude: number
        longitude: number
      } =>
        typeof store.latitude === "number" &&
        typeof store.longitude === "number"
    )
  }, [stores])


  const bounds = useMemo(() => {
    const points: [number, number][] =
      plottedStores.map((store) => [
        store.longitude,
        store.latitude,
      ])

    if (
      typeof dcLatitude === "number" &&
      typeof dcLongitude === "number"
    ) {
      points.push([dcLongitude, dcLatitude])
    }

    if (points.length === 0) {
      return null
    }

    const nextBounds = new mapboxgl.LngLatBounds()

    points.forEach(([longitude, latitude]) => {
      nextBounds.extend([longitude, latitude])
    })

    return nextBounds
  }, [
    plottedStores,
    dcLatitude,
    dcLongitude,
  ])


  const hasDcCoordinates =
    typeof dcLatitude === "number" &&
    typeof dcLongitude === "number"


  const hasAnyCoordinates =
    hasDcCoordinates ||
    plottedStores.length > 0


  if (!hasAnyCoordinates) {
    return (
      <div
        className="flex min-h-[310px] items-center justify-center rounded-[24px] border px-6 text-center"
        style={{
          background:
            "radial-gradient(circle at center, #F9F4EA 0%, #F2ECE1 100%)",
          borderColor: theme.line,
        }}
      >
        <div>
          <div
            className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl"
            style={{
              background: "#F3ECE6",
              color: theme.coral,
            }}
          >
            <Warehouse className="h-5 w-5" />
          </div>

          <div
            className="mt-3 text-sm font-semibold"
            style={{ color: theme.charcoal }}
          >
            Store locations unavailable
          </div>

          <div
            className="mt-1 text-xs"
            style={{ color: theme.brown }}
          >
            Coordinates will appear here once geocoding is complete.
          </div>
        </div>
      </div>
    )
  }


  return (
    <div
      className="relative min-h-[310px] overflow-hidden rounded-[24px] border"
      style={{
        borderColor: theme.line,
      }}
    >
      <Map
        mapboxAccessToken={
          process.env.NEXT_PUBLIC_MAPBOX_TOKEN
        }
        mapStyle="mapbox://styles/mapbox/light-v11"
        style={{
          width: "100%",
          height: "310px",
        }}
        initialViewState={{
          longitude:
            dcLongitude ??
            plottedStores[0]?.longitude ??
            -98.5,

          latitude:
            dcLatitude ??
            plottedStores[0]?.latitude ??
            39.5,

          zoom: 5,
        }}
        bounds={
          bounds
            ? [
                bounds.getWest(),
                bounds.getSouth(),
                bounds.getEast(),
                bounds.getNorth(),
              ]
            : undefined
        }
        fitBoundsOptions={{
          padding: 55,
          maxZoom: 10,
        }}
        attributionControl={false}
        reuseMaps
      >
        <NavigationControl
          position="top-right"
          showCompass={false}
          visualizePitch={false}
        />


        {plottedStores.map((store) => (
          <Marker
            key={store.coded_customer}
            longitude={store.longitude}
            latitude={store.latitude}
            anchor="center"
          >
            <button
              type="button"
              onMouseEnter={() =>
                setHoveredStore(store)
              }
              onMouseLeave={() =>
                setHoveredStore(null)
              }
              className="flex h-3 w-3 items-center justify-center rounded-full border-2 border-white shadow-sm transition-transform hover:scale-125"
              style={{
                background: theme.secondary,
              }}
              aria-label={
                store.coded_customer ??
                "Store location"
              }
            />
          </Marker>
        ))}


        {hasDcCoordinates && (
          <Marker
            longitude={dcLongitude}
            latitude={dcLatitude}
            anchor="center"
          >
            <div
              className="flex h-12 w-12 items-center justify-center rounded-2xl border-4 border-white shadow-lg"
              style={{
                background: theme.coral,
                color: "#FFFFFF",
              }}
              title={dcName ?? dcCode}
            >
              <Warehouse className="h-5 w-5" />
            </div>
          </Marker>
        )}


        {hoveredStore &&
          typeof hoveredStore.latitude ===
            "number" &&
          typeof hoveredStore.longitude ===
            "number" && (
            <Popup
              longitude={
                hoveredStore.longitude
              }
              latitude={
                hoveredStore.latitude
              }
              anchor="bottom"
              offset={12}
              closeButton={false}
              closeOnClick={false}
              className="dc-store-popup"
            >
              <div className="min-w-[180px] px-1 py-1">
                <div className="flex items-start gap-2">
                  <div
                    className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                    style={{
                      background: "#F3ECE6",
                      color: theme.coral,
                    }}
                  >
                    <Store className="h-3.5 w-3.5" />
                  </div>

                  <div>
                    <div
                      className="text-xs font-semibold"
                      style={{
                        color:
                          theme.charcoal,
                      }}
                    >
                      {hoveredStore.coded_customer ??
                        "Store"}
                    </div>

                    <div
                      className="mt-0.5 text-[11px]"
                      style={{
                        color:
                          theme.brown,
                      }}
                    >
                      {[
                        hoveredStore.chain,
                        hoveredStore.state,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  </div>
                </div>
              </div>
            </Popup>
          )}
      </Map>


      <div
        className="pointer-events-none absolute bottom-3 left-3 rounded-full border bg-white/90 px-3 py-1.5 text-[11px] font-medium shadow-sm backdrop-blur"
        style={{
          borderColor: theme.line,
          color: theme.brown,
        }}
      >
        {plottedStores.length} stores mapped
      </div>
    </div>
  )
}