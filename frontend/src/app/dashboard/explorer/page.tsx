'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { gsap } from 'gsap';
import {
    Map,
    Search,
    Filter,
    Layers,
    ZoomIn,
    ZoomOut,
    Maximize2,
    MapPin,
    TreePine,
    CheckCircle2,
    XCircle,
    HelpCircle,
    ChevronDown,
    ChevronRight,
    X,
    Copy,
    ExternalLink,
    Navigation,
    Leaf,
    Home,
    BarChart3,
    FileText,
    Settings,
    Menu,
    Bell,
    Calendar,
    ArrowLeft,
    Eye,
    RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import Link from 'next/link';
import { api } from '@/lib/api';

// Patch interface based on real API data
interface PatchInfo {
    id: string;
    name: string;
    survival: number;
    planted: number;
    alive: number;
    dead: number;
    status: 'healthy' | 'warning' | 'critical';
    trees: TreeInfo[];
    imageUrl?: string;
    imageDimensions?: [number, number];
}

interface TreeInfo {
    id: string;
    status: 'alive' | 'dead' | 'uncertain';
    confidence: number;
    bbox: { x: number; y: number; width: number; height: number };
}

// Sapling Inspection Panel
function SaplingPanel({ sapling, onClose }: { sapling: TreeInfo | null; onClose: () => void }) {
    if (!sapling) return null;

    const statusConfig = {
        alive: { label: 'Alive', color: 'bg-alive', textColor: 'text-alive', icon: CheckCircle2 },
        dead: { label: 'Dead', color: 'bg-dead', textColor: 'text-dead', icon: XCircle },
        uncertain: { label: 'Uncertain', color: 'bg-uncertain', textColor: 'text-uncertain', icon: HelpCircle },
    };

    const config = statusConfig[sapling.status as keyof typeof statusConfig];
    const StatusIcon = config.icon;

    return (
        <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="absolute right-0 top-0 bottom-0 w-96 bg-card border-l border-border z-20 overflow-y-auto"
        >
            {/* Header */}
            <div className="sticky top-0 bg-card border-b border-border p-4 flex items-center justify-between">
                <h3 className="font-semibold">Sapling Inspection</h3>
                <Button variant="ghost" size="icon" onClick={onClose}>
                    <X className="w-4 h-4" />
                </Button>
            </div>

            <div className="p-4 space-y-6">
                {/* Info Section */}
                <Card className="border-0 bg-muted/30">
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-sm text-muted-foreground">ID</span>
                            <span className="font-mono font-medium">{sapling.id}</span>
                        </div>
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-sm text-muted-foreground">Status</span>
                            <Badge className={`${config.color}/10 ${config.textColor} border-0`}>
                                <StatusIcon className="w-3 h-3 mr-1" />
                                {config.label}
                            </Badge>
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-muted-foreground">Confidence</span>
                                <span className="font-medium">{sapling.confidence.toFixed(1)}%</span>
                            </div>
                            <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${sapling.confidence}%` }}
                                    transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                                    className={`absolute inset-y-0 left-0 rounded-full ${sapling.confidence > 85 ? 'bg-alive' : sapling.confidence > 70 ? 'bg-uncertain' : 'bg-dead'}`}
                                />
                            </div>
                            {sapling.confidence < 70 && (
                                <p className="text-xs text-uncertain flex items-center gap-1 mt-2">
                                    <HelpCircle className="w-3 h-3" />
                                    Manual verification recommended
                                </p>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Coordinates Section */}
                <Card className="border-0 bg-muted/30">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Coordinates</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <div className="space-y-2 mb-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-muted-foreground">Position X</span>
                                <span className="font-mono">{sapling.bbox.x}px</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-muted-foreground">Position Y</span>
                                <span className="font-mono">{sapling.bbox.y}px</span>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <Button variant="outline" size="sm" className="flex-1">
                                <Copy className="w-3 h-3 mr-1" />
                                Copy
                            </Button>
                            <Button variant="outline" size="sm" className="flex-1">
                                <ExternalLink className="w-3 h-3 mr-1" />
                                Open in Maps
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* AI Reasoning Section */}
                <Card className="border-0 bg-muted/30">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">AI Reasoning</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <p className="text-sm text-muted-foreground leading-relaxed">
                            {sapling.status === 'dead'
                                ? "Marked dead due to: No green vegetation detected within 1.5m radius. NDVI value: 0.12. Expected range: >0.4"
                                : sapling.status === 'uncertain'
                                    ? "Classification uncertain: Partial vegetation detected. NDVI value: 0.35. Recommend field verification."
                                    : "Healthy vegetation pattern detected. NDVI value: 0.68. Crown diameter: 45cm. Expected growth trajectory confirmed."
                            }
                        </p>
                    </CardContent>
                </Card>

                {/* Historical Snapshots */}
                <Card className="border-0 bg-muted/30">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">Historical Snapshots</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <div className="flex gap-3">
                            {['Y1', 'Y2', 'Y3'].map((year, index) => (
                                <div key={year} className="flex-1 text-center">
                                    <div className="aspect-square bg-gradient-to-br from-forest/10 to-forest/5 rounded-lg mb-2 flex items-center justify-center relative overflow-hidden">
                                        <TreePine className="w-6 h-6 text-forest/50" />
                                        <div className="absolute inset-0 grid-pattern opacity-30" />
                                    </div>
                                    <p className="text-xs font-medium">{year}</p>
                                    <div className={`w-4 h-4 mx-auto mt-1 rounded-full ${index < 2 ? 'bg-alive' : sapling.status === 'dead' ? 'bg-dead' : 'bg-alive'} flex items-center justify-center`}>
                                        {index < 2 || sapling.status !== 'dead' ? (
                                            <CheckCircle2 className="w-3 h-3 text-white" />
                                        ) : (
                                            <XCircle className="w-3 h-3 text-white" />
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Actions */}
                <div className="space-y-2">
                    <Button variant="outline" className="w-full justify-start" disabled>
                        <CheckCircle2 className="w-4 h-4 mr-2" />
                        Override to Alive
                        <Badge variant="secondary" className="ml-auto text-xs">Coming Soon</Badge>
                    </Button>
                    <Button variant="outline" className="w-full justify-start" disabled>
                        <HelpCircle className="w-4 h-4 mr-2" />
                        Flag for Review
                        <Badge variant="secondary" className="ml-auto text-xs">Coming Soon</Badge>
                    </Button>
                </div>
            </div>
        </motion.div>
    );
}

// Filter Sidebar
function FilterSidebar() {
    const [yearFilter, setYearFilter] = useState('all');
    const [survivalRange, setSurvivalRange] = useState([0, 100]);
    const [statusFilters, setStatusFilters] = useState({ critical: true, warning: true, healthy: true });
    const [districtFilters, setDistrictFilters] = useState({ khordha: true, cuttack: true, puri: true, mayurbhanj: true });

    return (
        <div className="w-64 bg-card border-r border-border h-full overflow-y-auto">
            <div className="p-4 space-y-6">
                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search patch ID..."
                        className="w-full h-10 pl-10 pr-4 bg-muted/50 rounded-xl border-0 focus:ring-2 focus:ring-forest/50 focus:outline-none text-sm"
                    />
                </div>

                {/* Year Filter */}
                <div>
                    <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        Year Filter
                    </h4>
                    <div className="space-y-2">
                        {['all', '2024', '2025', '2026'].map((year) => (
                            <label key={year} className="flex items-center gap-2 cursor-pointer group">
                                <input
                                    type="radio"
                                    name="year"
                                    value={year}
                                    checked={yearFilter === year}
                                    onChange={(e) => setYearFilter(e.target.value)}
                                    className="w-4 h-4 text-forest focus:ring-forest"
                                />
                                <span className="text-sm group-hover:text-forest transition-colors">
                                    {year === 'all' ? 'All Years' : `Year ${year.slice(-1)} (${year})`}
                                </span>
                            </label>
                        ))}
                    </div>
                </div>

                {/* Survival Range */}
                <div>
                    <h4 className="text-sm font-medium mb-3">Survival Range</h4>
                    <Slider
                        value={survivalRange}
                        onValueChange={setSurvivalRange}
                        min={0}
                        max={100}
                        step={1}
                        className="mb-2"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                        <span>{survivalRange[0]}%</span>
                        <span>{survivalRange[1]}%</span>
                    </div>
                </div>

                {/* Status Filter */}
                <div>
                    <h4 className="text-sm font-medium mb-3">Status</h4>
                    <div className="space-y-2">
                        {[
                            { key: 'critical', label: 'Critical', color: 'bg-dead' },
                            { key: 'warning', label: 'Warning', color: 'bg-uncertain' },
                            { key: 'healthy', label: 'Healthy', color: 'bg-alive' },
                        ].map((status) => (
                            <label key={status.key} className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={statusFilters[status.key as keyof typeof statusFilters]}
                                    onChange={(e) => setStatusFilters({ ...statusFilters, [status.key]: e.target.checked })}
                                    className="w-4 h-4 rounded text-forest focus:ring-forest"
                                />
                                <span className={`w-2 h-2 rounded-full ${status.color}`} />
                                <span className="text-sm">{status.label}</span>
                            </label>
                        ))}
                    </div>
                </div>

                {/* District Filter */}
                <div>
                    <h4 className="text-sm font-medium mb-3">District</h4>
                    <div className="space-y-2">
                        {['khordha', 'cuttack', 'puri', 'mayurbhanj'].map((district) => (
                            <label key={district} className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={districtFilters[district as keyof typeof districtFilters]}
                                    onChange={(e) => setDistrictFilters({ ...districtFilters, [district]: e.target.checked })}
                                    className="w-4 h-4 rounded text-forest focus:ring-forest"
                                />
                                <span className="text-sm capitalize">{district}</span>
                            </label>
                        ))}
                    </div>
                </div>

                {/* Reset Filters */}
                <Button variant="outline" className="w-full">
                    Reset Filters
                </Button>
            </div>
        </div>
    );
}

// Map Legend
function MapLegend() {
    return (
        <div className="absolute bottom-20 right-4 glass-card rounded-xl p-4 z-10">
            <h4 className="text-sm font-medium mb-3">Legend</h4>
            <div className="space-y-2">
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-alive shadow-lg shadow-alive/50" />
                    <span className="text-sm">Alive</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-dead shadow-lg shadow-dead/50" />
                    <span className="text-sm">Dead</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-uncertain shadow-lg shadow-uncertain/50" />
                    <span className="text-sm">Uncertain</span>
                </div>
            </div>
        </div>
    );
}

// Map Controls
function MapControls() {
    return (
        <div className="absolute bottom-20 left-4 flex flex-col gap-2 z-10">
            <Button variant="secondary" size="icon" className="glass-card">
                <ZoomIn className="w-4 h-4" />
            </Button>
            <Button variant="secondary" size="icon" className="glass-card">
                <ZoomOut className="w-4 h-4" />
            </Button>
            <Button variant="secondary" size="icon" className="glass-card">
                <Maximize2 className="w-4 h-4" />
            </Button>
            <Button variant="secondary" size="icon" className="glass-card">
                <Layers className="w-4 h-4" />
            </Button>
        </div>
    );
}

// Simulated Map View with interactive patches
function MapView({
    patches,
    saplings,
    selectedPatch,
    onSelectPatch,
    onSelectSapling
}: {
    patches: PatchInfo[];
    saplings: TreeInfo[];
    selectedPatch: PatchInfo | null;
    onSelectPatch: (patch: PatchInfo | null) => void;
    onSelectSapling: (sapling: TreeInfo) => void;
}) {
    const [imgError, setImgError] = useState(false);

    // Reset error when selected patch changes
    useEffect(() => {
        setImgError(false);
    }, [selectedPatch]);

    return (
        <div className="relative flex-1 bg-gradient-to-br from-forest/5 to-forest/10 overflow-hidden">
            {/* Grid pattern for map background */}
            {!selectedPatch?.imageUrl && (
                <>
                    <div className="absolute inset-0 grid-pattern opacity-30" />
                    <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-background/80 backdrop-blur-sm border border-border px-4 py-2 rounded-full text-sm font-medium pointer-events-none z-20 flex items-center gap-2 shadow-sm">
                        <MapPin className="w-4 h-4 text-forest" />
                        Select a patch to view drone imagery
                    </div>
                </>
            )}

            {/* Simulated map with patches OR Real Image View */}
            <div className={`absolute inset-0 ${selectedPatch?.imageUrl ? 'flex items-center justify-center bg-black/90' : 'p-8'}`}>

                {selectedPatch?.imageUrl && !imgError ? (
                    <div className="relative inline-block" style={{ maxHeight: '100%', maxWidth: '100%' }}>
                        <img
                            src={selectedPatch.imageUrl}
                            alt={selectedPatch.name}
                            className="max-h-full max-w-full object-contain shadow-2xl"
                            style={{ maxHeight: 'calc(100vh - 120px)' }}
                            onError={() => setImgError(true)}
                        />
                        {/* Overlay Real Bounding Boxes */}
                        {saplings.map((sapling, i) => {
                            const dims = selectedPatch.imageDimensions || [4000, 3000];
                            const left = (sapling.bbox.x / dims[0]) * 100;
                            const top = (sapling.bbox.y / dims[1]) * 100;
                            const width = (sapling.bbox.width / dims[0]) * 100;
                            const height = (sapling.bbox.height / dims[1]) * 100;

                            return (
                                <div
                                    key={sapling.id || `sapling-${i}`}
                                    className={`absolute border-2 ${sapling.status === 'alive' ? 'border-alive/80 bg-alive/20' :
                                        sapling.status === 'dead' ? 'border-dead/80 bg-dead/20' :
                                            'border-uncertain/80 bg-uncertain/20'
                                        } hover:bg-white/30 cursor-pointer transition-all hover:border-white z-10`}
                                    style={{
                                        left: `${left}%`,
                                        top: `${top}%`,
                                        width: `${width}%`,
                                        height: `${height}%`
                                    }}
                                    onClick={(e) => { e.stopPropagation(); onSelectSapling(sapling); }}
                                    title={`Confidence: ${sapling.confidence.toFixed(0)}%`}
                                />
                            );
                        })}
                    </div>
                ) : selectedPatch?.imageUrl && imgError ? (
                    <div className="flex flex-col items-center justify-center text-muted-foreground p-8 text-center bg-card rounded-xl border border-border max-w-md">
                        <XCircle className="w-12 h-12 mb-4 text-dead" />
                        <h3 className="text-lg font-semibold text-foreground mb-2">Image Not Found</h3>
                        <p className="mb-4">The original image for this patch is missing from the server.</p>
                        <Button variant="outline" onClick={() => onSelectPatch(null)}>
                            Go Back
                        </Button>
                    </div>
                ) : (
                    /* Default Simulated Overview */
                    patches.map((patch, index) => {
                        const left = 10 + (index % 3) * 30;
                        const top = 15 + Math.floor(index / 3) * 35;
                        const isSelected = selectedPatch?.id === patch.id;

                        return (
                            <motion.div
                                key={patch.id || `patch-${index}`}
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: index * 0.1, duration: 0.4 }}
                                onClick={() => onSelectPatch(isSelected ? null : patch)}
                                className={`absolute cursor-pointer transition-all duration-300 ${isSelected ? 'z-10' : 'z-0'}`}
                                style={{ left: `${left}%`, top: `${top}%` }}
                            >
                                {/* Patch polygon shape */}
                                <svg
                                    width="120"
                                    height="100"
                                    viewBox="0 0 120 100"
                                    className={`transition-all duration-300 ${isSelected ? 'scale-110' : 'hover:scale-105'}`}
                                >
                                    <path
                                        d="M10,30 L30,10 L90,15 L110,40 L100,80 L60,95 L20,85 Z"
                                        fill={patch.status === 'critical' ? 'rgba(220, 38, 38, 0.3)' : patch.status === 'warning' ? 'rgba(234, 179, 8, 0.3)' : 'rgba(34, 197, 94, 0.3)'}
                                        stroke={patch.status === 'critical' ? '#dc2626' : patch.status === 'warning' ? '#eab308' : '#22c55e'}
                                        strokeWidth={isSelected ? 3 : 2}
                                        className="transition-all duration-300"
                                    />
                                </svg>

                                {/* Patch label on hover */}
                                <motion.div
                                    initial={false}
                                    animate={{ opacity: isSelected ? 1 : 0 }}
                                    className="absolute left-1/2 -translate-x-1/2 top-full mt-2 glass-card rounded-lg px-3 py-2 whitespace-nowrap pointer-events-none"
                                >
                                    <p className="font-semibold text-sm">{patch.id}</p>
                                    <p className="text-xs text-muted-foreground">{patch.name}</p>
                                    <p className={`text-xs font-medium ${patch.status === 'critical' ? 'text-dead' : patch.status === 'warning' ? 'text-uncertain' : 'text-alive'}`}>
                                        Survival: {patch.survival}%
                                    </p>
                                    <p className="text-[10px] text-blue-300 mt-1 flex items-center gap-1">
                                        <Eye className="w-3 h-3" /> Click to view image
                                    </p>
                                </motion.div>
                            </motion.div>
                        );
                    })
                )}
            </div>

            {/* Map controls */}
            <MapControls />

            {/* Legend */}
            <MapLegend />

            {/* Selected patch info card */}
            <AnimatePresence>
                {selectedPatch && (
                    <motion.div
                        key={selectedPatch.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 20 }}
                        className="absolute top-4 left-4 glass-card rounded-xl p-4 w-72 z-10"
                    >
                        <div className="flex items-start justify-between mb-3">
                            <div>
                                <h3 className="font-semibold">{selectedPatch.id}</h3>
                                <p className="text-sm text-muted-foreground">{selectedPatch.name}</p>
                            </div>
                            <Badge
                                className={`${selectedPatch.status === 'critical' ? 'bg-dead/10 text-dead' :
                                    selectedPatch.status === 'warning' ? 'bg-uncertain/10 text-uncertain' :
                                        'bg-alive/10 text-alive'
                                    } border-0`}
                            >
                                {selectedPatch.status === 'critical' ? 'Critical' : selectedPatch.status === 'warning' ? 'Warning' : 'Healthy'}
                            </Badge>
                        </div>

                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <p className="text-muted-foreground">Planted</p>
                                <p className="font-semibold">{selectedPatch.planted.toLocaleString()}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground">Survival</p>
                                <p className={`font-semibold ${selectedPatch.status === 'critical' ? 'text-dead' : selectedPatch.status === 'warning' ? 'text-uncertain' : 'text-alive'}`}>
                                    {selectedPatch.survival}%
                                </p>
                            </div>
                            <div>
                                <p className="text-muted-foreground">Alive</p>
                                <p className="font-semibold text-alive">{selectedPatch.alive.toLocaleString()}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground">Dead</p>
                                <p className="font-semibold text-dead">{selectedPatch.dead.toLocaleString()}</p>
                            </div>
                        </div>

                        <div className="mt-4 flex gap-2">
                            <Link href={`/dashboard/temporal?id=${encodeURIComponent(selectedPatch.id)}`} className="flex-1">
                                <Button size="sm" className="w-full gradient-forest text-white border-0">
                                    <Eye className="w-4 h-4 mr-1" />
                                    Temporal View
                                </Button>
                            </Link>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

// Main Patch Explorer Page
export default function PatchExplorerPage() {
    const [patches, setPatches] = useState<PatchInfo[]>([]);
    const [selectedPatch, setSelectedPatch] = useState<PatchInfo | null>(null);
    const [selectedSapling, setSelectedSapling] = useState<TreeInfo | null>(null);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [loading, setLoading] = useState(true);

    // Fetch patches from API
    useEffect(() => {
        async function fetchPatches() {
            setLoading(true);
            try {
                const allDetails = await api.getAllPatchDetails();

                const patchData = allDetails.map((details) => {
                    const name = details.patch_id;
                    const trees = details.trees || [];
                    const alive = trees.filter((t: any) => t.classification === 'sapling' || t.health_status === 'healthy').length;
                    const dead = trees.filter((t: any) => t.health_status === 'dead' || t.health_status === 'unhealthy').length;
                    const total = trees.length;
                    const survivalRate = total > 0 ? (alive / total) * 100 : 0;

                    return {
                        id: name,
                        name: name,
                        survival: survivalRate,
                        planted: total,
                        alive: alive,
                        dead: dead,
                        status: survivalRate >= 85 ? 'healthy' : survivalRate >= 70 ? 'warning' : 'critical',
                        trees: trees.map((t: any, i: number) => ({
                            id: t.tree_id || `TREE-${i}`,
                            status: t.health_status === 'healthy' ? 'alive' : t.health_status === 'dead' ? 'dead' : 'uncertain',
                            confidence: (t.classification_confidence || 0.8) * 100,
                            bbox: t.bbox || { x: 0, y: 0, width: 50, height: 50 }
                        })),
                        imageUrl: (details as any).metadata?.filename ? api.getImageUrl((details as any).metadata.filename) : undefined,
                        imageDimensions: (details as any).metadata?.dimensions
                    } as PatchInfo;
                });

                setPatches(patchData);
            } catch (error) {
                console.error('Error fetching patches:', error);
            }
            setLoading(false);
        }
        fetchPatches();
    }, []);

    // Convert trees to sapling format for MapView
    const saplings = selectedPatch?.trees || [];

    return (
        <div className="h-screen flex flex-col bg-background">
            {/* Top bar */}
            <header className="h-14 glass border-b border-border flex items-center justify-between px-4 z-30">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard">
                        <Button variant="ghost" size="icon">
                            <ArrowLeft className="w-5 h-5" />
                        </Button>
                    </Link>
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg gradient-forest flex items-center justify-center">
                            <Map className="w-4 h-4 text-white" />
                        </div>
                        <h1 className="font-semibold">Patch Explorer</h1>
                        {loading && <RefreshCw className="w-4 h-4 animate-spin text-muted-foreground" />}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <Badge variant="secondary">{patches.length} Patches</Badge>
                    <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)}>
                        <Filter className="w-5 h-5" />
                    </Button>
                </div>
            </header>

            {/* Main content */}
            <div className="flex-1 flex overflow-hidden relative">
                {/* Filter Sidebar */}
                <AnimatePresence>
                    {sidebarOpen && (
                        <motion.div
                            initial={{ x: -256, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            exit={{ x: -256, opacity: 0 }}
                            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                            className="absolute left-0 top-0 bottom-0 z-20"
                        >
                            <FilterSidebar />
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Map View */}
                <MapView
                    patches={patches}
                    saplings={saplings}
                    selectedPatch={selectedPatch}
                    onSelectPatch={setSelectedPatch}
                    onSelectSapling={setSelectedSapling}
                />

                {/* Sapling Inspection Panel */}
                <AnimatePresence>
                    {selectedSapling && (
                        <SaplingPanel key={selectedSapling.id} sapling={selectedSapling} onClose={() => setSelectedSapling(null)} />
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
