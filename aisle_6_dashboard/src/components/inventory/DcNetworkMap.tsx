"use client"

import { useMemo, useState } from "react"
import Map, {
  Marker,
  NavigationControl,
  Popup,
} from "react-map-gl/mapbox"
import mapboxgl from "mapbox-gl"
import { Store, Warehouse } from "lucide-react"


type MapStore = {
  coded_customer: string | null
  chain: string | null
  channel?: string | null
  state?: string | null
  latitude?: number | null
  longitude?: number | null
}


export type MapDistributionCenter = {
  distributor: string
  dc: string
  dc_name?: string | null
  dc_latitude?: number | null
  dc_longitude?: number | null
  dc_location_precision?: string | null
  active_store_count?: number | null
  stores?: MapStore[]

  quantity_on_hand_cases?: number | null
  quantity_on_po_cases?: number | null
  velocity_cases_per_week?: number | null
  weeks_on_hand?: number | null
  oos_events_l6m?: number | null
  oos_history_complete?: boolean
  planning_lead_time_days?: number | null

  sku_count?: number | null
  skus_below_3_woh?: number | null
  skus_3_to_4_woh?: number | null
  skus_4_plus_woh?: number | null
  skus_woh_unavailable?: number | null
  skus_oos?: number | null
}


type DcNetworkMapProps = {
  distributionCenters: MapDistributionCenter[]
  onDcClick?: (
    distributionCenter: MapDistributionCenter
  ) => void
}


const theme = {
  coral: "#EE6A4C",
  purple: "#9A93B0",
  secondary: "#C58E82",
  charcoal: "#343332",
  brown: "#705C4F",
  line: "#EEE5D8",
}

function DcSkuState({
  dc,
}: {
  dc: MapDistributionCenter
}) {
  const below =
    dc.skus_below_3_woh ?? 0
  const middle =
    dc.skus_3_to_4_woh ?? 0
  const above =
    dc.skus_4_plus_woh ?? 0
  const unavailable =
    dc.skus_woh_unavailable ?? 0

  const knownCount =
    below + middle + above

  if (knownCount === 0) {
    return (
      <div
        className="text-[11px] font-medium"
        style={{ color: "#9A8E82" }}
      >
        WOH unavailable
      </div>
    )
  }

  const belowPct =
    (below / knownCount) * 100
  const middlePct =
    (middle / knownCount) * 100
  const abovePct =
    (above / knownCount) * 100

  return (
    <div>
      <div
        className="mb-2 text-[10px] font-medium uppercase tracking-wide"
        style={{ color: theme.brown }}
      >
        SKU inventory state
      </div>

      <div className="flex h-2 overflow-hidden rounded-full bg-[#EEE8DF]">
        {below > 0 && (
          <div
            style={{
              width: `${belowPct}%`,
              background: "#D99A82",
            }}
          />
        )}

        {middle > 0 && (
          <div
            style={{
              width: `${middlePct}%`,
              background: "#D6BE8E",
            }}
          />
        )}

        {above > 0 && (
          <div
            style={{
              width: `${abovePct}%`,
              background: "#9FAF9E",
            }}
          />
        )}
      </div>

      <div
        className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[10px] font-medium"
        style={{ color: theme.brown }}
      >
        {below > 0 && (
          <span>{below} below 3</span>
        )}

        {middle > 0 && (
          <span>{middle} at 3–4</span>
        )}

        {above > 0 && (
          <span>{above} at 4+</span>
        )}

        {unavailable > 0 && (
          <span>
            {unavailable} unavailable
          </span>
        )}
      </div>
    </div>
  )
}


export default function DcNetworkMap({
  distributionCenters,
  onDcClick,
}: DcNetworkMapProps) {
  const [hoveredStore, setHoveredStore] =
    useState<
      | (MapStore & {
          distributor: string
          dc: string
        })
      | null
    >(null)

  const [hoveredDc, setHoveredDc] =
    useState<MapDistributionCenter | null>(
      null
    )


  const plottedDcs = useMemo(() => {
    return distributionCenters.filter(
      (
        dc
      ): dc is MapDistributionCenter & {
        dc_latitude: number
        dc_longitude: number
      } =>
        typeof dc.dc_latitude === "number" &&
        typeof dc.dc_longitude === "number"
    )
  }, [distributionCenters])


  const plottedStores = useMemo(() => {
    return distributionCenters.flatMap(
      (dc) =>
        (dc.stores ?? [])
          .filter(
            (
              store
            ): store is MapStore & {
              latitude: number
              longitude: number
            } =>
              typeof store.latitude ===
                "number" &&
              typeof store.longitude ===
                "number"
          )
          .map((store) => ({
            ...store,
            distributor: dc.distributor,
            dc: dc.dc,
          }))
    )
  }, [distributionCenters])


  // Initial map framing is based only on DCs.
  // Store locations still render, but Alaska / Hawaii
  // stores do not force the initial view to zoom out.
  const bounds = useMemo(() => {
    if (plottedDcs.length === 0) {
      return null
    }

    const nextBounds =
      new mapboxgl.LngLatBounds()

    plottedDcs.forEach((dc) => {
      nextBounds.extend([
        Number(dc.dc_longitude),
        Number(dc.dc_latitude),
      ])
    })

    return nextBounds
  }, [plottedDcs])


  if (
    plottedDcs.length === 0 &&
    plottedStores.length === 0
  ) {
    return (
      <div
        className="flex min-h-[430px] items-center justify-center rounded-[24px] border px-6 text-center"
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
            style={{
              color: theme.charcoal,
            }}
          >
            Network locations unavailable
          </div>

          <div
            className="mt-1 text-xs"
            style={{
              color: theme.brown,
            }}
          >
            DC and store coordinates are not
            available yet.
          </div>
        </div>
      </div>
    )
  }


  return (
    <div
      className="relative min-h-[430px] overflow-hidden rounded-[24px] border"
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
          height: "430px",
        }}
        initialViewState={
          bounds
            ? {
                bounds: [
                  [
                    bounds.getWest(),
                    bounds.getSouth(),
                  ],
                  [
                    bounds.getEast(),
                    bounds.getNorth(),
                  ],
                ],
                fitBoundsOptions: {
                  padding: 55,
                  maxZoom: 8,
                },
              }
            : {
                longitude: -98.5,
                latitude: 39.5,
                zoom: 3,
              }
        }
        attributionControl
        reuseMaps
      >
        <NavigationControl
          position="top-right"
          showCompass={false}
          visualizePitch={false}
        />


        {/* Store markers */}
        {plottedStores.map(
          (store, index) => (
            <Marker
              key={`${store.distributor}-${store.dc}-${store.coded_customer ?? index}`}
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
                className="flex h-2.5 w-2.5 items-center justify-center rounded-full border border-white shadow-sm transition-transform hover:scale-150"
                style={{
                  background:
                    theme.secondary,
                }}
                aria-label={
                  store.coded_customer ??
                  "Store location"
                }
              />
            </Marker>
          )
        )}


        {/* DC markers */}
        {plottedDcs.map((dc) => {
          const dcColor =
            dc.distributor === "UNFI"
              ? theme.coral
              : theme.purple

          return (
            <Marker
              key={`${dc.distributor}-${dc.dc}`}
              longitude={dc.dc_longitude}
              latitude={dc.dc_latitude}
              anchor="center"
            >
              <button
                type="button"
                onMouseEnter={() =>
                  setHoveredDc(dc)
                }
                onMouseLeave={() =>
                  setHoveredDc(null)
                }
                onClick={() =>
                  onDcClick?.(dc)
                }
                className="group flex flex-col items-center"
                aria-label={`${dc.distributor} ${dc.dc}`}
              >
                <div
                  className="flex h-12 w-12 items-center justify-center rounded-2xl border-4 border-white shadow-lg transition-transform group-hover:scale-110"
                  style={{
                    background: dcColor,
                    color: "#FFFFFF",
                  }}
                >
                  <Warehouse className="h-5 w-5" />
                </div>

                <div
                  className="mt-1 rounded-full border bg-white/95 px-2 py-0.5 text-[10px] font-bold shadow-sm"
                  style={{
                    borderColor: theme.line,
                    color: theme.charcoal,
                  }}
                >
                  {dc.dc}
                </div>
              </button>
            </Marker>
          )
        })}


        {/* Store popup */}
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
            >
              <div className="min-w-[180px] px-1 py-1">
                <div className="flex items-start gap-2">
                  <div
                    className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                    style={{
                      background:
                        "#F3ECE6",
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

                    <div
                      className="mt-1 text-[10px] font-medium"
                      style={{
                        color:
                          theme.brown,
                      }}
                    >
                      {hoveredStore.distributor}{" "}
                      {hoveredStore.dc}
                    </div>
                  </div>
                </div>
              </div>
            </Popup>
          )}


        {/* DC popup */}
        {hoveredDc &&
          typeof hoveredDc.dc_latitude ===
            "number" &&
          typeof hoveredDc.dc_longitude ===
            "number" && (
            <Popup
            longitude={hoveredDc.dc_longitude}
            latitude={hoveredDc.dc_latitude}
            anchor="left"
            offset={32}
            closeButton={false}
            closeOnClick={false}
            maxWidth="380px"
            >
            <div className="w-[340px] px-1 py-1">
                {/* Header */}
                <div className="flex items-start gap-3">
                  <div
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
                    style={{
                      background:
                        hoveredDc.distributor ===
                        "UNFI"
                          ? "#FCEDE8"
                          : "#F0EDF5",
                      color:
                        hoveredDc.distributor ===
                        "UNFI"
                          ? theme.coral
                          : theme.purple,
                    }}
                  >
                    <Warehouse className="h-4 w-4" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div
                      className="text-sm font-semibold leading-tight"
                      style={{
                        color:
                          theme.charcoal,
                      }}
                    >
                      {hoveredDc.dc_name ??
                        hoveredDc.dc}
                    </div>

                    <div
                      className="mt-1 flex items-center gap-1.5 text-[11px]"
                      style={{
                        color:
                          theme.brown,
                      }}
                    >
                      <span
                        className="rounded-full px-2 py-0.5 font-semibold"
                        style={{
                          background:
                            hoveredDc.distributor ===
                            "UNFI"
                              ? "#FCEDE8"
                              : "#F0EDF5",
                          color:
                            hoveredDc.distributor ===
                            "UNFI"
                              ? theme.coral
                              : theme.purple,
                        }}
                      >
                        {hoveredDc.distributor}
                      </span>

                      <span>
                        {hoveredDc.dc}
                      </span>
                    </div>
                  </div>
                </div>


                {/* Metrics */}
                <div
                  className="mt-3 grid grid-cols-2 gap-x-5 gap-y-2 border-t pt-3"
                  style={{
                    borderColor:
                      theme.line,
                  }}
                >
                  <div>
                    <div
                      className="text-[10px] font-medium uppercase tracking-wide"
                      style={{
                        color:
                          theme.brown,
                      }}
                    >
                      On hand
                    </div>

                    <div
                      className="mt-0.5 text-sm font-semibold"
                      style={{
                        color:
                          theme.charcoal,
                      }}
                    >
                      {hoveredDc.quantity_on_hand_cases !=
                      null
                        ? `${Math.round(
                            hoveredDc.quantity_on_hand_cases
                          ).toLocaleString()} cases`
                        : "—"}
                    </div>
                  </div>


                  <div>
                    <div
                      className="text-[10px] font-medium uppercase tracking-wide"
                      style={{
                        color:
                          theme.brown,
                      }}
                    >
                      Open PO
                    </div>

                    <div
                      className="mt-0.5 text-sm font-semibold"
                      style={{
                        color:
                          theme.charcoal,
                      }}
                    >
                      {hoveredDc.quantity_on_po_cases !=
                      null
                        ? `${Math.round(
                            hoveredDc.quantity_on_po_cases
                          ).toLocaleString()} cases`
                        : "—"}
                    </div>
                  </div>


                  <div>
                    <div
                      className="text-[10px] font-medium uppercase tracking-wide"
                      style={{
                        color:
                          theme.brown,
                      }}
                    >
                      Weeks on hand
                    </div>

                    <div
                      className="mt-0.5 text-sm font-semibold"
                      style={{
                        color:
                          theme.charcoal,
                      }}
                    >
                      {hoveredDc.weeks_on_hand !=
                      null
                        ? `${hoveredDc.weeks_on_hand.toFixed(
                            1
                          )} wks`
                        : "—"}
                    </div>
                  </div>


                  <div>
                    <div
                      className="text-[10px] font-medium uppercase tracking-wide"
                      style={{
                        color:
                          theme.brown,
                      }}
                    >
                      Velocity
                    </div>

                    <div
                      className="mt-0.5 text-sm font-semibold"
                      style={{
                        color:
                          theme.charcoal,
                      }}
                    >
                      {hoveredDc.velocity_cases_per_week !=
                      null
                        ? `${hoveredDc.velocity_cases_per_week.toFixed(
                            1
                          )} cases/wk`
                        : "—"}
                    </div>
                  </div>
                </div>

                {/* SKU inventory state */}
                <div
                className="mt-3 border-t pt-3"
                style={{
                    borderColor: theme.line,
                }}
                >
                <DcSkuState dc={hoveredDc} />
                </div>


                {/* Footer */}
                <div
                  className="mt-3 flex items-center justify-between border-t pt-2.5 text-[11px]"
                  style={{
                    borderColor:
                      theme.line,
                    color:
                      theme.brown,
                  }}
                >
                  <span>
                    {hoveredDc.active_store_count ??
                      0}{" "}
                    active stores
                  </span>

                  <span>
                    {hoveredDc.oos_events_l6m ??
                      0}{" "}
                    OOS events · L6M
                  </span>
                </div>
              </div>
            </Popup>
          )}
      </Map>


      <div
        className="pointer-events-none absolute top-3 left-3 rounded-full border bg-white/90 px-3 py-1.5 text-[11px] font-medium shadow-sm backdrop-blur"
        style={{
          borderColor: theme.line,
          color: theme.brown,
        }}
      >
        {plottedDcs.length} DCs ·{" "}
        {plottedStores.length} stores mapped
      </div>
    </div>
  )
}