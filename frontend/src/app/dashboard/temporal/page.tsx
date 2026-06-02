'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ArrowLeft,
    Layers,
    Eye,
    EyeOff,
    Calendar,
    ChevronLeft,
    ChevronRight,
    Maximize2,
    Download,
    GripVertical,
    CheckCircle2,
    XCircle,
    TreePine,
    Info,
    RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { api, PatchData } from '@/lib/api';

// Comparison Slider Component
function ComparisonSlider({
    leftLabel,
    rightLabel,
    leftDate,
    rightDate,
    showOverlay,
    overlayOpacity,
    patchData,
    imageUrl
}: {
    leftLabel: string;
    rightLabel: string;
    leftDate: string;
    rightDate: string;
    showOverlay: boolean;
    overlayOpacity: number;
    patchData: PatchData | null;
    imageUrl?: string;
}) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [sliderPosition, setSliderPosition] = useState(50);
    const [isDragging, setIsDragging] = useState(false);
    const [imgError, setImgError] = useState(false);

    const handleMouseDown = () => setIsDragging(true);
    const handleMouseUp = () => setIsDragging(false);

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDragging || !containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
        setSliderPosition(percentage);
    };

    const handleTouchMove = (e: React.TouchEvent) => {
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const x = e.touches[0].clientX - rect.left;
        const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
        setSliderPosition(percentage);
    };

    // Calculate sapling positions using REAL data only
    const mapSaplings = () => {
        if (!patchData || !patchData.trees) return [];

        // Default to a 4:3 aspect ratio coordinate system if dimensions are missing
        const imgWidth = patchData.metadata?.dimensions?.[0] || 4000;
        const imgHeight = patchData.metadata?.dimensions?.[1] || 3000;

        return patchData.trees.map(tree => ({
            id: tree.tree_id,
            x: (tree.bbox.x / imgWidth) * 100,
            y: (tree.bbox.y / imgHeight) * 100,
            // Use correct backend field: 'status' is uppercase ALIVE/DEAD/DISEASED
            status: (tree.status || '').toUpperCase() === 'ALIVE' ? 'alive' : 'dead'
        }));
    };

    const saplings = mapSaplings();

    return (
        <div
            ref={containerRef}
            className="relative w-full h-full overflow-hidden cursor-ew-resize select-none bg-black/5"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onTouchMove={handleTouchMove}
        >
            {/* Left Image (Historical/Previous) - NO MOCKS */}
            <div className="absolute inset-0 bg-neutral-100 flex items-center justify-center">
                <div className="text-center p-8 opacity-50">
                    <Layers className="w-12 h-12 mx-auto mb-2 text-neutral-400" />
                    <p className="font-semibold text-neutral-500">No Historical Data</p>
                    <p className="text-xs text-neutral-400">First survey point recorded</p>
                </div>
                {/* Label */}
                <div className="absolute top-4 left-4 bg-white/50 backdrop-blur rounded-lg px-3 py-2 z-10 border border-black/5">
                    <p className="font-semibold text-sm">{leftLabel}</p>
                    <p className="text-xs text-muted-foreground">{leftDate || 'N/A'}</p>
                </div>
            </div>

            {/* Right Image (Current/Actual) - Clipped */}
            <div
                className="absolute inset-0 bg-background"
                style={{ clipPath: `inset(0 0 0 ${sliderPosition}%)` }}
            >
                {imageUrl && !imgError ? (
                    <img
                        src={imageUrl}
                        alt="Current Patch State"
                        className="absolute inset-0 w-full h-full object-contain bg-black/5"
                        onError={() => setImgError(true)}
                    />
                ) : (
                    <div className="absolute inset-0 flex items-center justify-center bg-muted">
                        <div className="text-center">
                            <TreePine className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                            <p className="text-muted-foreground text-sm">Image Pending Upload</p>
                        </div>
                    </div>
                )}

                {/* Label */}
                <div className="absolute top-4 right-4 glass-card rounded-lg px-3 py-2 z-10">
                    <p className="font-semibold text-sm">{rightLabel}</p>
                    <p className="text-xs text-muted-foreground">{rightDate}</p>
                </div>

                {/* AI Overlay using REAL Data */}
                <AnimatePresence>
                    {showOverlay && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: overlayOpacity / 100 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0"
                        >
                            {saplings.map((sapling) => (
                                <motion.div
                                    key={sapling.id}
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    className={`absolute w-4 h-4 rounded-full flex items-center justify-center transform -translate-x-1/2 -translate-y-1/2 cursor-help ${sapling.status === 'alive' ? 'bg-alive/60 border border-alive' : 'bg-dead/60 border border-dead'
                                        }`}
                                    style={{ left: `${sapling.x}%`, top: `${sapling.y}%` }}
                                    title={`Parameters: ${sapling.status}`}
                                >
                                </motion.div>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Slider Handle */}
            <motion.div
                className="absolute top-0 bottom-0 w-1 bg-white shadow-lg cursor-ew-resize z-20"
                style={{ left: `${sliderPosition}%`, transform: 'translateX(-50%)' }}
                onMouseDown={handleMouseDown}
                onTouchStart={() => setIsDragging(true)}
                onTouchEnd={() => setIsDragging(false)}
            >
                {/* Handle grip */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white shadow-xl flex items-center justify-center">
                    <GripVertical className="w-5 h-5 text-forest" />
                </div>

                {/* Arrows */}
                <div className="absolute top-1/2 -translate-y-1/2 left-1/2 -translate-x-[calc(50%+30px)]">
                    <ChevronLeft className="w-6 h-6 text-white drop-shadow-lg" />
                </div>
                <div className="absolute top-1/2 -translate-y-1/2 left-1/2 -translate-x-[calc(50%-30px)]">
                    <ChevronRight className="w-6 h-6 text-white drop-shadow-lg" />
                </div>
            </motion.div>
        </div>
    );
}

// Timeline Selector
function TimelineSelector({
    selectedStage,
    onSelectStage
}: {
    selectedStage: string;
    onSelectStage: (stage: string) => void;
}) {
    const stages = [
        { id: 'op1', label: 'T-2', date: 'Historical', description: 'Pit Stage' },
        { id: 'op2', label: 'T-1', date: 'Previous', description: 'Initial Growth' },
        { id: 'op3', label: 'Current', date: 'Latest Upload', description: 'Sapling Stage' },
    ];

    return (
        <div className="flex items-center justify-center gap-2 p-4">
            {stages.map((stage, index) => (
                <div key={stage.id} className="flex items-center">
                    <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => onSelectStage(stage.id)}
                        className={`relative px-4 py-2 rounded-xl transition-all ${selectedStage === stage.id
                            ? 'bg-forest text-white'
                            : 'bg-muted hover:bg-muted/80'
                            }`}
                    >
                        <span className="font-semibold text-sm">{stage.label}</span>
                        <span className="block text-xs opacity-70">{stage.date}</span>
                    </motion.button>

                    {index < stages.length - 1 && (
                        <div className={`w-8 h-0.5 mx-1 bg-forest/30`} />
                    )}
                </div>
            ))}
        </div>
    );
}

// Control Panel
function ControlPanel({
    showOverlay,
    onToggleOverlay,
    overlayOpacity,
    onOpacityChange,
    viewMode,
    onViewModeChange
}: {
    showOverlay: boolean;
    onToggleOverlay: () => void;
    overlayOpacity: number;
    onOpacityChange: (value: number) => void;
    viewMode: string;
    onViewModeChange: (mode: string) => void;
}) {
    return (
        <div className="bg-card border-t border-border p-4">
            <div className="max-w-4xl mx-auto flex flex-wrap items-center justify-between gap-4">
                {/* AI Overlay Toggle */}
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <Switch
                            checked={showOverlay}
                            onCheckedChange={onToggleOverlay}
                            className="data-[state=checked]:bg-forest"
                        />
                        <span className="text-sm font-medium">AI Overlay</span>
                        {showOverlay ? <Eye className="w-4 h-4 text-forest" /> : <EyeOff className="w-4 h-4 text-muted-foreground" />}
                    </div>

                    {/* Opacity Slider */}
                    <AnimatePresence>
                        {showOverlay && (
                            <motion.div
                                initial={{ opacity: 0, width: 0 }}
                                animate={{ opacity: 1, width: 'auto' }}
                                exit={{ opacity: 0, width: 0 }}
                                className="flex items-center gap-2 overflow-hidden"
                            >
                                <span className="text-xs text-muted-foreground">Opacity</span>
                                <Slider
                                    value={[overlayOpacity]}
                                    onValueChange={(value) => onOpacityChange(value[0])}
                                    min={0}
                                    max={100}
                                    step={1}
                                    className="w-24"
                                />
                                <span className="text-xs font-mono w-8">{overlayOpacity}%</span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* View Mode Toggle */}
                <Tabs value={viewMode} onValueChange={onViewModeChange}>
                    <TabsList className="grid grid-cols-2 h-9">
                        <TabsTrigger value="slider" className="text-xs px-3">Slider</TabsTrigger>
                        <TabsTrigger value="overlay" className="text-xs px-3">Full View</TabsTrigger>
                    </TabsList>
                </Tabs>

                {/* Actions */}
                <div className="flex items-center gap-2">
                    <Button variant="ghost" size="icon">
                        <Maximize2 className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon">
                        <Download className="w-4 h-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}

// Patch Info Card
function PatchInfoCard({ patchData }: { patchData: PatchData | null }) {
    if (!patchData) return null;

    const summary = patchData.summary;
    const total = summary.total_trees;
    const alive = summary.alive_trees;
    const survivalRate = total > 0 ? (alive / total) * 100 : 0;

    return (
        <Card className="glass-card">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-medium break-all">{patchData.patch_id}</CardTitle>
                    <Badge className={survivalRate >= 85 ? "bg-alive/10 text-alive border-0" : "bg-dead/10 text-dead border-0"}>
                        {survivalRate >= 85 ? 'Healthy' : 'Critical'}
                    </Badge>
                </div>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <p className="text-muted-foreground">Location</p>
                        <p className="font-medium">Block A (Auto)</p>
                    </div>
                    <div>
                        <p className="text-muted-foreground">Survival Rate</p>
                        <p className={`font-medium ${survivalRate >= 85 ? 'text-alive' : 'text-dead'}`}>
                            {survivalRate.toFixed(1)}%
                        </p>
                    </div>
                    <div>
                        <p className="text-muted-foreground">Total Planted</p>
                        <p className="font-medium">{total.toLocaleString()}</p>
                    </div>
                    <div>
                        <p className="text-muted-foreground">Detection</p>
                        <p className="font-medium">AI Analysis</p>
                    </div>
                </div>

                <div className="mt-4 p-3 bg-muted/50 rounded-lg flex items-start gap-2">
                    <Info className="w-4 h-4 text-forest mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground">
                        Viewing real-time AI analysis results.
                        Historical comparison simulated until more data is available.
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}

// Main Temporal Comparison Page
export default function TemporalComparisonPage() {
    const searchParams = useSearchParams();
    const patchId = searchParams.get('id');

    const [showOverlay, setShowOverlay] = useState(true);
    const [overlayOpacity, setOverlayOpacity] = useState(70);
    const [selectedStage, setSelectedStage] = useState('op3'); // Default to current
    const [viewMode, setViewMode] = useState('slider');

    const [patchData, setPatchData] = useState<PatchData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            if (!patchId) {
                setLoading(false); // stop spinner — nothing to load
                return;
            }
            setLoading(true);
            try {
                const data = await api.getPatchDetails(patchId);
                setPatchData(data);
            } catch (err) {
                console.error("Failed to load patch data", err);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [patchId]);

    const imageUrl = patchData?.metadata?.filename ? api.getImageUrl(patchData.metadata.filename as string) : undefined;
    const stageData = {
        op1: { label: 'T-2', date: 'Historical' },
        op2: { label: 'T-1', date: 'Previous' },
        op3: { label: 'Current', date: 'Latest Upload' },
    };

    const currentStage = stageData[selectedStage as keyof typeof stageData];

    // Show empty state when no patch is selected
    if (!loading && !patchId) {
        return (
            <div className="h-screen flex flex-col items-center justify-center bg-background gap-6">
                <div className="w-20 h-20 rounded-2xl gradient-forest flex items-center justify-center">
                    <Layers className="w-10 h-10 text-white" />
                </div>
                <div className="text-center">
                    <h2 className="text-2xl font-bold mb-2">No Patch Selected</h2>
                    <p className="text-muted-foreground max-w-sm">
                        Navigate to the Patch Explorer, select a patch, and open it in the Temporal View.
                    </p>
                </div>
                <Link href="/dashboard/explorer">
                    <Button className="bg-forest hover:bg-forest/90">
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Go to Patch Explorer
                    </Button>
                </Link>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col bg-background">
            {/* Top bar */}
            <header className="h-14 glass border-b border-border flex items-center justify-between px-4 z-30">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard/explorer">
                        <Button variant="ghost" size="icon">
                            <ArrowLeft className="w-5 h-5" />
                        </Button>
                    </Link>
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg gradient-forest flex items-center justify-center">
                            <Layers className="w-4 h-4 text-white" />
                        </div>
                        <div>
                            <h1 className="font-semibold leading-tight">Temporal Comparison</h1>
                            <p className="text-xs text-muted-foreground">
                                {patchId || 'Select a patch'}
                            </p>
                        </div>
                        {loading && <RefreshCw className="w-4 h-4 animate-spin ml-2 text-muted-foreground" />}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm">
                        <Calendar className="w-4 h-4 mr-2" />
                        Date
                    </Button>
                </div>
            </header>

            {/* Main Content */}
            <div className="flex-1 flex overflow-hidden">
                {/* Comparison View */}
                <div className="flex-1 flex flex-col">
                    {/* Timeline */}
                    <TimelineSelector selectedStage={selectedStage} onSelectStage={setSelectedStage} />

                    {/* Comparison Slider */}
                    <div className="flex-1 relative bg-black/5">
                        <ComparisonSlider
                            leftLabel={selectedStage === 'op3' ? 'Simulation' : currentStage.label}
                            rightLabel="Current Logic"
                            leftDate="Reference"
                            rightDate="Today"
                            showOverlay={showOverlay}
                            overlayOpacity={overlayOpacity}
                            patchData={patchData}
                            imageUrl={imageUrl} // Only passes image if available
                        />
                    </div>

                    {/* Control Panel */}
                    <ControlPanel
                        showOverlay={showOverlay}
                        onToggleOverlay={() => setShowOverlay(!showOverlay)}
                        overlayOpacity={overlayOpacity}
                        onOpacityChange={setOverlayOpacity}
                        viewMode={viewMode}
                        onViewModeChange={setViewMode}
                    />
                </div>

                {/* Side Panel */}
                <div className="w-80 border-l border-border bg-card p-4 hidden lg:block overflow-y-auto">
                    {patchData ? (
                        <>
                            <PatchInfoCard patchData={patchData} />

                            {/* Detection Summary */}
                            <Card className="glass-card mt-4">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg font-medium">Detection Summary</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-alive" />
                                            <span className="text-sm">Alive</span>
                                        </div>
                                        <span className="font-semibold text-alive">
                                            {patchData.summary.alive_trees.toLocaleString()} ({
                                                patchData.summary.total_trees > 0
                                                    ? ((patchData.summary.alive_trees / patchData.summary.total_trees) * 100).toFixed(1)
                                                    : 0
                                            }%)
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-dead" />
                                            <span className="text-sm">Dead</span>
                                        </div>
                                        <span className="font-semibold text-dead">
                                            {patchData.summary.dead_trees.toLocaleString()} ({
                                                patchData.summary.total_trees > 0
                                                    ? ((patchData.summary.dead_trees / patchData.summary.total_trees) * 100).toFixed(1)
                                                    : 0
                                            }%)
                                        </span>
                                    </div>
                                    <div className="pt-4 border-t border-border">
                                        <div className="flex items-center justify-between text-sm">
                                            <span className="text-muted-foreground">Algo Confidence</span>
                                            <span className="font-semibold">94.2%</span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </>
                    ) : (
                        <div className="flex items-center justify-center h-full text-muted-foreground">
                            Select a patch to view details
                        </div>
                    )}

                    {/* Actions */}
                    <div className="mt-4 space-y-2">
                        <Button className="w-full gradient-forest text-white border-0">
                            <Download className="w-4 h-4 mr-2" />
                            Export Data
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
