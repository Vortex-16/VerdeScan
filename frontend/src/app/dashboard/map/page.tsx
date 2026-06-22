'use client';

import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
    ArrowLeft, Map, RefreshCw, Download,
    Activity, Menu, Target,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import DashboardSidebar from '@/components/DashboardSidebar';
import { api, SiteResult, SiteMarker, SurveyPoint, EvalResult } from '@/lib/api';

// Leaflet imports must be dynamic — it uses browser APIs
const LeafletMap = dynamic(() => import('@/components/FieldLeafletMap'), {
    ssr: false,
    loading: () => (
        <div className="flex-1 flex items-center justify-center bg-muted/20">
            <div className="flex items-center gap-3 text-muted-foreground">
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Loading map…</span>
            </div>
        </div>
    ),
});

const SITES = [
    { value: 'benkmura', label: 'Benkmura VF', planted: 8_000 },
    { value: 'debadihi', label: 'Debadihi VF', planted: 10_000 },
] as const;

type SiteKey = 'benkmura' | 'debadihi';

function StatChip({ label, value, color }: { label: string; value: string; color?: string }) {
    return (
        <div className="flex flex-col items-center bg-muted/40 rounded-xl px-4 py-3 min-w-[90px]">
            <span className={`text-xl font-semibold ${color ?? ''}`}>{value}</span>
            <span className="text-xs text-muted-foreground mt-0.5">{label}</span>
        </div>
    );
}

function LayerToggle({
    label, count, color, active, onToggle,
}: { label: string; count: number; color: string; active: boolean; onToggle: () => void }) {
    return (
        <button
            onClick={onToggle}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all text-sm font-medium ${
                active ? 'border-transparent' : 'border-border bg-muted/30 opacity-50'
            }`}
            style={active ? { borderColor: color, background: `${color}18` } : undefined}
        >
            <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: color }} />
            <span>{label}</span>
            <Badge variant="secondary" className="ml-1 text-xs px-1.5 py-0">{count.toLocaleString()}</Badge>
        </button>
    );
}

export default function FieldMapPage() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [site, setSite] = useState<SiteKey>('benkmura');
    const [result, setResult] = useState<SiteResult | null>(null);
    const [surveys, setSurveys] = useState<SurveyPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [showAlive, setShowAlive] = useState(true);
    const [showDead, setShowDead] = useState(true);
    const [showSurveys, setShowSurveys] = useState(true);
    const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
    const [showTruth, setShowTruth] = useState(true);
    const [evalBusy, setEvalBusy] = useState(false);
    const [evalError, setEvalError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const fetchResult = async (s: SiteKey) => {
        setLoading(true);
        setEvalResult(null);       // ground truth is per-site — clear on switch
        setEvalError(null);
        const [r, sv] = await Promise.all([
            api.getSiteResult(s),
            api.getSiteSurveys(s),
        ]);
        setResult(r);
        setSurveys(sv?.surveys ?? []);
        setLoading(false);
    };

    const handleEvaluate = async (file: File) => {
        setEvalBusy(true);
        setEvalError(null);
        const res = await api.evaluateSite(site, file);
        if (res.ok) {
            setEvalResult(res.result);
            setShowTruth(true);
        } else {
            setEvalError(res.error);
            setEvalResult(null);
        }
        setEvalBusy(false);
    };

    useEffect(() => {
        fetchResult(site);
    }, [site]);

    const handleAnalyze = async () => {
        setRunning(true);
        await api.analyzeSite(site);
        const deadline = Date.now() + 1800_000;
        const poll = async () => {
            const [r, sv] = await Promise.all([
                api.getSiteResult(site),
                api.getSiteSurveys(site),
            ]);
            if (r) setResult(r);
            setSurveys(sv?.surveys ?? []);
            if (r?.status === 'complete') { setRunning(false); return; }
            if (Date.now() < deadline) setTimeout(poll, 5000);
            else setRunning(false);
        };
        setTimeout(poll, 3000);
    };

    const downloadGeoJSON = async () => {
        const r = result;
        if (!r) return;
        const features = [
            ...(r.alive_locations ?? []).map((m: SiteMarker) => ({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [m.lon, m.lat] },
                properties: { status: 'alive', confidence: m.conf },
            })),
            ...(r.casualties ?? []).map((m: SiteMarker) => ({
                type: 'Feature',
                geometry: { type: 'Point', coordinates: [m.lon, m.lat] },
                properties: { status: 'dead', confidence: m.conf },
            })),
        ];
        const blob = new Blob([JSON.stringify({ type: 'FeatureCollection', features }, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `${site}_all_detections.geojson`;
        a.click(); URL.revokeObjectURL(url);
    };

    const siteInfo = SITES.find(s => s.value === site)!;
    const isComplete = result?.status === 'complete';
    const aliveLocations = result?.alive_locations ?? [];
    const deadLocations = result?.casualties ?? [];

    const visibleAlive    = showAlive   ? aliveLocations  : [];
    const visibleDead     = showDead    ? deadLocations    : [];
    const visibleSurveys  = showSurveys ? surveys          : [];
    const visibleTruth    = showTruth   ? (evalResult?.points ?? []) : [];

    return (
        <div className="h-screen flex flex-col bg-background overflow-hidden">
            <DashboardSidebar activePage="Field Map" isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

            <div className="lg:pl-64 flex flex-col h-full">
                {/* Header */}
                <header className="h-14 glass border-b border-border flex items-center justify-between px-4 flex-shrink-0 z-20">
                    <div className="flex items-center gap-3">
                        <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
                            <Menu className="w-5 h-5" />
                        </Button>
                        <Link href="/dashboard">
                            <Button variant="ghost" size="icon">
                                <ArrowLeft className="w-5 h-5" />
                            </Button>
                        </Link>
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg gradient-forest flex items-center justify-center">
                                <Map className="w-4 h-4 text-white" />
                            </div>
                            <h1 className="font-semibold">Field Map</h1>
                            {(loading || running) && <RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" />}
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {/* Site selector */}
                        <select
                            value={site}
                            onChange={e => setSite(e.target.value as SiteKey)}
                            className="h-9 px-3 bg-muted/50 rounded-lg border-0 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-forest/40"
                        >
                            {SITES.map(s => (
                                <option key={s.value} value={s.value}>{s.label}</option>
                            ))}
                        </select>

                        {/* Trigger analysis */}
                        {!isComplete && !running && (
                            <Button
                                size="sm"
                                onClick={handleAnalyze}
                                className="gradient-forest text-white border-0"
                            >
                                Run Analysis
                            </Button>
                        )}

                        {/* Evaluate vs ground truth (judging criterion #1) */}
                        {isComplete && (
                            <>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept=".geojson,.json,.csv,.kml,.gpx,.xml"
                                    className="hidden"
                                    onChange={(e) => {
                                        const f = e.target.files?.[0];
                                        if (f) handleEvaluate(f);
                                        e.target.value = '';   // allow re-uploading the same file
                                    }}
                                />
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={evalBusy}
                                    title="Upload known-dead GPS points (GeoJSON/CSV/KML/GPX) to score recall"
                                >
                                    {evalBusy
                                        ? <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
                                        : <Target className="w-4 h-4 mr-1" />}
                                    Evaluate
                                </Button>
                            </>
                        )}

                        {/* Download */}
                        {isComplete && (
                            <Button variant="outline" size="sm" onClick={downloadGeoJSON}>
                                <Download className="w-4 h-4 mr-1" />
                                GeoJSON
                            </Button>
                        )}
                    </div>
                </header>

                {evalError && (
                    <div className="flex-shrink-0 px-4 py-2 bg-red-500/10 text-red-500 text-sm border-b border-red-500/20">
                        Evaluation failed: {evalError}
                    </div>
                )}

                {/* Stats bar */}
                {isComplete && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex-shrink-0 px-4 py-3 border-b border-border bg-card/80 backdrop-blur-sm flex flex-wrap items-center gap-3 z-10"
                    >
                        <StatChip label="Pits Classified" value={(result!.in_field ?? 0).toLocaleString()} />
                        <StatChip label="Alive" value={(result!.alive ?? 0).toLocaleString()} color="text-alive" />
                        <StatChip label="Dead" value={(result!.dead ?? 0).toLocaleString()} color="text-dead" />
                        <StatChip
                            label="Survival Rate"
                            value={result!.survival_pct != null ? `${result!.survival_pct}%` : '—'}
                            color={(result!.survival_pct ?? 0) >= 75 ? 'text-alive' : 'text-dead'}
                        />
                        {(result!.no_data ?? 0) > 0 && (
                            <StatChip
                                label="No-Data (skipped)"
                                value={(result!.no_data ?? 0).toLocaleString()}
                                color="text-muted-foreground"
                            />
                        )}

                        {/* Recall vs ground truth — appears once a known-dead file is scored */}
                        {evalResult && (
                            <>
                                <div className="w-px h-10 bg-border mx-1" />
                                <StatChip
                                    label={`Recall (${evalResult.matched}/${evalResult.total_truth} dead)`}
                                    value={`${evalResult.recall}%`}
                                    color={evalResult.recall >= 80 ? 'text-alive' : 'text-dead'}
                                />
                                {evalResult.mean_dist != null && (
                                    <StatChip
                                        label="Mean match Δ"
                                        value={`${evalResult.mean_dist} m`}
                                        color="text-muted-foreground"
                                    />
                                )}
                            </>
                        )}

                        <div className="ml-auto flex items-center gap-2 flex-wrap">
                            <LayerToggle
                                label="Alive"
                                count={aliveLocations.length}
                                color="#22c55e"
                                active={showAlive}
                                onToggle={() => setShowAlive(v => !v)}
                            />
                            <LayerToggle
                                label="Dead"
                                count={deadLocations.length}
                                color="#dc2626"
                                active={showDead}
                                onToggle={() => setShowDead(v => !v)}
                            />
                            {surveys.length > 0 && (
                                <LayerToggle
                                    label="Surveys"
                                    count={surveys.length}
                                    color="#a855f7"
                                    active={showSurveys}
                                    onToggle={() => setShowSurveys(v => !v)}
                                />
                            )}
                            {evalResult && (
                                <LayerToggle
                                    label="Ground truth"
                                    count={evalResult.points.length}
                                    color="#14b8a6"
                                    active={showTruth}
                                    onToggle={() => setShowTruth(v => !v)}
                                />
                            )}
                        </div>
                    </motion.div>
                )}

                {/* Map area */}
                <div className="flex-1 relative overflow-hidden">
                    {!isComplete && !loading ? (
                        /* Empty state */
                        <div className="absolute inset-0 flex items-center justify-center">
                            <Card className="glass-card max-w-sm mx-4">
                                <CardContent className="p-8 text-center">
                                    <div className="w-16 h-16 rounded-full gradient-forest mx-auto mb-4 flex items-center justify-center">
                                        <Activity className="w-8 h-8 text-white" />
                                    </div>
                                    <h3 className="text-lg font-semibold mb-2">No Data for {siteInfo.label}</h3>
                                    <p className="text-sm text-muted-foreground mb-4">
                                        Run the orthomosaic analysis pipeline to generate GPS-precise tree locations
                                        for all {siteInfo.planted.toLocaleString()} planted pits.
                                    </p>
                                    <Button
                                        onClick={handleAnalyze}
                                        disabled={running}
                                        className="gradient-forest text-white border-0 w-full"
                                    >
                                        {running ? (
                                            <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Running…</>
                                        ) : (
                                            'Run Analysis (~7 min)'
                                        )}
                                    </Button>
                                </CardContent>
                            </Card>
                        </div>
                    ) : (
                        <LeafletMap
                            alive={visibleAlive}
                            dead={visibleDead}
                            surveys={visibleSurveys}
                            truth={visibleTruth}
                            site={site}
                            loading={loading}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}
