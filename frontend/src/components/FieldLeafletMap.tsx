'use client';

import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, ZoomControl } from 'react-leaflet';
import { SiteMarker, SurveyPoint } from '@/lib/api';
import 'leaflet/dist/leaflet.css';

// Site centre coordinates
const SITE_CENTRES: Record<string, [number, number]> = {
    benkmura: [21.655, 83.818],
    debadihi: [21.660, 83.825],
};

const ALIVE_COLOUR   = '#22c55e';
const DEAD_COLOUR    = '#dc2626';
const SURVEY_COLOUR  = '#a855f7';

function FlyTo({ site }: { site: string }) {
    const map = useMap();
    useEffect(() => {
        const centre = SITE_CENTRES[site];
        if (centre) map.flyTo(centre, 16, { duration: 1.2 });
    }, [site, map]);
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

    // Build markers — cap total to keep DOM lean
    const aliveMarkers = useMemo(() => alive.slice(0, 3000), [alive]);
    const deadMarkers  = useMemo(() => dead.slice(0, 2000), [dead]);

    return (
        <MapContainer
            center={centre}
            zoom={16}
            zoomControl={false}
            className="w-full h-full"
            style={{ background: '#0a0f0c' }}
        >
            {/* Satellite imagery tiles from ESRI */}
            <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP"
                maxZoom={20}
            />
            {/* Street name overlay so locations are readable */}
            <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
                attribution=""
                maxZoom={20}
                opacity={0.5}
            />

            <ZoomControl position="bottomright" />
            <FlyTo site={site} />

            {/* Alive markers — green circles */}
            {aliveMarkers.map((m, i) => (
                <CircleMarker
                    key={`a-${i}`}
                    center={[m.lat, m.lon]}
                    radius={4}
                    pathOptions={{
                        color: ALIVE_COLOUR,
                        fillColor: ALIVE_COLOUR,
                        fillOpacity: 0.75,
                        weight: 1,
                    }}
                >
                    <Popup>
                        <div className="text-sm">
                            <p className="font-semibold text-green-600">Alive</p>
                            <p className="text-xs text-muted-foreground">
                                Conf: {(m.conf * 100).toFixed(0)}%
                            </p>
                            <p className="text-xs font-mono">
                                {m.lat.toFixed(6)}, {m.lon.toFixed(6)}
                            </p>
                        </div>
                    </Popup>
                </CircleMarker>
            ))}

            {/* Dead markers — red circles */}
            {deadMarkers.map((m, i) => (
                <CircleMarker
                    key={`d-${i}`}
                    center={[m.lat, m.lon]}
                    radius={5}
                    pathOptions={{
                        color: DEAD_COLOUR,
                        fillColor: DEAD_COLOUR,
                        fillOpacity: 0.85,
                        weight: 1.5,
                    }}
                >
                    <Popup>
                        <div className="text-sm">
                            <p className="font-semibold text-red-600">Dead / Casualty</p>
                            <p className="text-xs text-muted-foreground">
                                Conf: {(m.conf * 100).toFixed(0)}%
                            </p>
                            <p className="text-xs font-mono">
                                {m.lat.toFixed(6)}, {m.lon.toFixed(6)}
                            </p>
                        </div>
                    </Popup>
                </CircleMarker>
            ))}

            {/* Survey point markers — purple squares (uploaded drone images) */}
            {surveys.map((s, i) => (
                <CircleMarker
                    key={`sv-${i}`}
                    center={[s.lat, s.lon]}
                    radius={8}
                    pathOptions={{
                        color: SURVEY_COLOUR,
                        fillColor: SURVEY_COLOUR,
                        fillOpacity: 0.9,
                        weight: 2,
                    }}
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
                                    {s.survival_pct != null && (
                                        <p>Survival: <strong>{s.survival_pct}%</strong></p>
                                    )}
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
    );
}
