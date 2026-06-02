'use client';

import { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, ZoomControl, useMapEvents } from 'react-leaflet';
import { SiteMarker, SurveyPoint } from '@/lib/api';
import 'leaflet/dist/leaflet.css';

const SITE_CENTRES: Record<string, [number, number]> = {
    benkmura: [21.655, 83.818],
    debadihi: [21.660, 83.825],
};

const ALIVE_COLOUR   = '#22c55e';
const DEAD_COLOUR    = '#dc2626';
const SURVEY_COLOUR  = '#a855f7';

// Maximum markers rendered at once. Above this we thin by confidence.
// Leaflet handles ~5 000 SVG circles comfortably; beyond that frame-rate drops.
const MAX_MARKERS = 5000;

function FlyTo({ site }: { site: string }) {
    const map = useMap();
    useEffect(() => {
        const centre = SITE_CENTRES[site];
        if (centre) map.flyTo(centre, 16, { duration: 1.2 });
    }, [site, map]);
    return null;
}

/** Reports current zoom so the parent can react */
function ZoomTracker({ onZoom }: { onZoom: (z: number) => void }) {
    useMapEvents({ zoomend: (e) => onZoom(e.target.getZoom()) });
    return null;
}

interface Props {
    alive: SiteMarker[];
    dead: SiteMarker[];
    surveys?: SurveyPoint[];
    site: string;
    loading: boolean;
}

export default function FieldLeafletMap({ alive, dead, surveys = [], site, loading }: Props) {
    const centre = SITE_CENTRES[site] ?? [21.655, 83.818];
    const [zoom, setZoom] = useState(16);

    const total = alive.length + dead.length;

    // At low zoom show a thinned sample sorted by confidence (highest first).
    // At high zoom (≥18) show everything — viewport is small so DOM count stays low.
    const { aliveMarkers, deadMarkers, thinned } = useMemo(() => {
        if (zoom >= 18 || total <= MAX_MARKERS) {
            return { aliveMarkers: alive, deadMarkers: dead, thinned: false };
        }
        // How many of each to keep, proportional to their share of total
        const aliveShare = alive.length / total;
        const keepAlive = Math.floor(MAX_MARKERS * aliveShare);
        const keepDead  = MAX_MARKERS - keepAlive;
        // Sort by confidence descending so highest-quality detections survive the cut
        const sortedAlive = [...alive].sort((a, b) => b.conf - a.conf).slice(0, keepAlive);
        const sortedDead  = [...dead ].sort((a, b) => b.conf - a.conf).slice(0, keepDead);
        return { aliveMarkers: sortedAlive, deadMarkers: sortedDead, thinned: true };
    }, [alive, dead, total, zoom]);

    return (
        <div className="relative w-full h-full">
            {thinned && (
                <div className="absolute top-2 left-1/2 -translate-x-1/2 z-[1000] pointer-events-none">
                    <div className="bg-black/70 text-white text-xs px-3 py-1.5 rounded-full flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-yellow-400 flex-shrink-0" />
                        Showing {MAX_MARKERS.toLocaleString()} of {total.toLocaleString()} markers — zoom in to see all
                    </div>
                </div>
            )}

            <MapContainer
                center={centre}
                zoom={zoom}
                zoomControl={false}
                className="w-full h-full"
                style={{ background: '#0a0f0c' }}
            >
                <TileLayer
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    attribution="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP"
                    maxZoom={20}
                />
                <TileLayer
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                    attribution=""
                    maxZoom={20}
                    opacity={0.5}
                />

                <ZoomControl position="bottomright" />
                <FlyTo site={site} />
                <ZoomTracker onZoom={setZoom} />

                {aliveMarkers.map((m, i) => (
                    <CircleMarker
                        key={`a-${i}`}
                        center={[m.lat, m.lon]}
                        radius={4}
                        pathOptions={{ color: ALIVE_COLOUR, fillColor: ALIVE_COLOUR, fillOpacity: 0.75, weight: 1 }}
                    >
                        <Popup>
                            <div className="text-sm">
                                <p className="font-semibold text-green-600">Alive</p>
                                <p className="text-xs text-muted-foreground">Conf: {(m.conf * 100).toFixed(0)}%</p>
                                <p className="text-xs font-mono">{m.lat.toFixed(6)}, {m.lon.toFixed(6)}</p>
                            </div>
                        </Popup>
                    </CircleMarker>
                ))}

                {deadMarkers.map((m, i) => (
                    <CircleMarker
                        key={`d-${i}`}
                        center={[m.lat, m.lon]}
                        radius={5}
                        pathOptions={{ color: DEAD_COLOUR, fillColor: DEAD_COLOUR, fillOpacity: 0.85, weight: 1.5 }}
                    >
                        <Popup>
                            <div className="text-sm">
                                <p className="font-semibold text-red-600">Dead / Casualty</p>
                                <p className="text-xs text-muted-foreground">Conf: {(m.conf * 100).toFixed(0)}%</p>
                                <p className="text-xs font-mono">{m.lat.toFixed(6)}, {m.lon.toFixed(6)}</p>
                            </div>
                        </Popup>
                    </CircleMarker>
                ))}

                {surveys.map((s, i) => (
                    <CircleMarker
                        key={`sv-${i}`}
                        center={[s.lat, s.lon]}
                        radius={8}
                        pathOptions={{ color: SURVEY_COLOUR, fillColor: SURVEY_COLOUR, fillOpacity: 0.9, weight: 2 }}
                    >
                        <Popup>
                            <div className="text-sm min-w-[160px]">
                                <p className="font-semibold text-purple-600 mb-1">Survey Image</p>
                                <p className="font-medium truncate">{s.patch_id}</p>
                                {s.total_trees != null && (
                                    <div className="mt-1 space-y-0.5 text-xs">
                                        <p>Trees detected: <strong>{s.total_trees}</strong></p>
                                        <p className="text-green-600">Alive: <strong>{s.alive_trees ?? '—'}</strong></p>
                                        <p className="text-red-600">Dead: <strong>{s.dead_trees ?? '—'}</strong></p>
                                        {s.survival_pct != null && <p>Survival: <strong>{s.survival_pct}%</strong></p>}
                                    </div>
                                )}
                                <p className="text-xs font-mono text-muted-foreground mt-1">
                                    {s.lat.toFixed(5)}, {s.lon.toFixed(5)}
                                </p>
                            </div>
                        </Popup>
                    </CircleMarker>
                ))}
            </MapContainer>
        </div>
    );
}
