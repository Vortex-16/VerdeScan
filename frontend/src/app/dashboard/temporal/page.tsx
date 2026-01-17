'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform, animate } from 'framer-motion';
import { gsap } from 'gsap';
import {
    ArrowLeft,
    Layers,
    Eye,
    EyeOff,
    Calendar,
    ChevronLeft,
    ChevronRight,
    Play,
    Pause,
    Maximize2,
    Download,
    Settings,
    GripVertical,
    CheckCircle2,
    XCircle,
    HelpCircle,
    TreePine,
    Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';

// Simulated image URLs (using gradients for demo)
const mockImages = {
    op1: 'OP1 (Pit Stage)',
    op2: 'OP2 (Initial Growth)',
    op3: 'OP3 (Sapling Stage)',
};

// Mock sapling overlay data
const mockOverlayData = Array.from({ length: 30 }, (_, i) => ({
    id: i,
    x: 10 + (i % 6) * 15,
    y: 15 + Math.floor(i / 6) * 18,
    status: Math.random() > 0.15 ? 'alive' : 'dead',
}));

// Comparison Slider Component
function ComparisonSlider({
    leftLabel,
    rightLabel,
    leftDate,
    rightDate,
    showOverlay,
    overlayOpacity
}: {
    leftLabel: string;
    rightLabel: string;
    leftDate: string;
    rightDate: string;
    showOverlay: boolean;
    overlayOpacity: number;
}) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [sliderPosition, setSliderPosition] = useState(50);
    const [isDragging, setIsDragging] = useState(false);

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

    return (
        <div
            ref={containerRef}
            className="relative w-full h-full overflow-hidden cursor-ew-resize select-none"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onTouchMove={handleTouchMove}
        >
            {/* Left Image (Before) */}
            <div className="absolute inset-0 bg-gradient-to-br from-earth/20 to-earth/40">
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-earth/30 flex items-center justify-center">
                            <div className="w-8 h-8 rounded-full border-2 border-dashed border-earth/50" />
                        </div>
                        <p className="text-earth/70 text-sm">Pit Stage - Visible Holes</p>
                    </div>
                </div>
                {/* Grid pattern for pit stage */}
                <div className="absolute inset-0 opacity-20">
                    {Array.from({ length: 25 }).map((_, i) => (
                        <div
                            key={i}
                            className="absolute w-6 h-6 rounded-full border-2 border-earth/50"
                            style={{
                                left: `${10 + (i % 5) * 20}%`,
                                top: `${15 + Math.floor(i / 5) * 18}%`,
                            }}
                        />
                    ))}
                </div>
                {/* Label */}
                <div className="absolute top-4 left-4 glass-card rounded-lg px-3 py-2">
                    <p className="font-semibold text-sm">{leftLabel}</p>
                    <p className="text-xs text-muted-foreground">{leftDate}</p>
                </div>
            </div>

            {/* Right Image (After) - Clipped */}
            <div
                className="absolute inset-0 bg-gradient-to-br from-forest/20 to-alive/30"
                style={{ clipPath: `inset(0 0 0 ${sliderPosition}%)` }}
            >
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                        <TreePine className="w-16 h-16 mx-auto mb-4 text-alive/70" />
                        <p className="text-alive/70 text-sm">Sapling Stage - Vegetation Visible</p>
                    </div>
                </div>
                {/* Saplings */}
                <div className="absolute inset-0 opacity-30">
                    {Array.from({ length: 25 }).map((_, i) => (
                        <TreePine
                            key={i}
                            className={`absolute w-5 h-5 ${Math.random() > 0.15 ? 'text-alive' : 'text-dead'}`}
                            style={{
                                left: `${10 + (i % 5) * 20}%`,
                                top: `${15 + Math.floor(i / 5) * 18}%`,
                            }}
                        />
                    ))}
                </div>
                {/* Label */}
                <div className="absolute top-4 right-4 glass-card rounded-lg px-3 py-2">
                    <p className="font-semibold text-sm">{rightLabel}</p>
                    <p className="text-xs text-muted-foreground">{rightDate}</p>
                </div>

                {/* AI Overlay */}
                <AnimatePresence>
                    {showOverlay && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: overlayOpacity / 100 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0"
                        >
                            {mockOverlayData.map((sapling) => (
                                <motion.div
                                    key={sapling.id}
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ delay: sapling.id * 0.02 }}
                                    className={`absolute w-6 h-6 rounded-full flex items-center justify-center ${sapling.status === 'alive' ? 'bg-alive/80' : 'bg-dead/80'
                                        }`}
                                    style={{ left: `${sapling.x}%`, top: `${sapling.y}%` }}
                                >
                                    {sapling.status === 'alive' ? (
                                        <CheckCircle2 className="w-4 h-4 text-white" />
                                    ) : (
                                        <XCircle className="w-4 h-4 text-white" />
                                    )}
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
        { id: 'op1', label: 'OP1', date: 'Mar 2024', description: 'Pit Stage' },
        { id: 'op2', label: 'OP2', date: 'Jun 2024', description: 'Initial Growth' },
        { id: 'op3', label: 'OP3', date: 'Oct 2024', description: 'Sapling Stage' },
        { id: 'future', label: 'Y2', date: 'Mar 2025', description: 'Year 2 Survey', disabled: true },
    ];

    return (
        <div className="flex items-center justify-center gap-2 p-4">
            {stages.map((stage, index) => (
                <div key={stage.id} className="flex items-center">
                    <motion.button
                        whileHover={{ scale: stage.disabled ? 1 : 1.05 }}
                        whileTap={{ scale: stage.disabled ? 1 : 0.95 }}
                        onClick={() => !stage.disabled && onSelectStage(stage.id)}
                        disabled={stage.disabled}
                        className={`relative px-4 py-2 rounded-xl transition-all ${selectedStage === stage.id
                                ? 'bg-forest text-white'
                                : stage.disabled
                                    ? 'bg-muted text-muted-foreground cursor-not-allowed'
                                    : 'bg-muted hover:bg-muted/80'
                            }`}
                    >
                        <span className="font-semibold text-sm">{stage.label}</span>
                        <span className="block text-xs opacity-70">{stage.date}</span>
                    </motion.button>

                    {index < stages.length - 1 && (
                        <div className={`w-8 h-0.5 mx-1 ${stage.disabled ? 'bg-muted' : 'bg-forest/30'}`} />
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
                    <TabsList className="grid grid-cols-3 h-9">
                        <TabsTrigger value="slider" className="text-xs px-3">Slider</TabsTrigger>
                        <TabsTrigger value="side-by-side" className="text-xs px-3">Side-by-Side</TabsTrigger>
                        <TabsTrigger value="overlay" className="text-xs px-3">Overlay</TabsTrigger>
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
function PatchInfoCard() {
    return (
        <Card className="glass-card">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-medium">Patch KL-042</CardTitle>
                    <Badge className="bg-alive/10 text-alive border-0">Healthy</Badge>
                </div>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <p className="text-muted-foreground">Location</p>
                        <p className="font-medium">Khordha Zone A</p>
                    </div>
                    <div>
                        <p className="text-muted-foreground">Survival Rate</p>
                        <p className="font-medium text-alive">87.2%</p>
                    </div>
                    <div>
                        <p className="text-muted-foreground">Total Planted</p>
                        <p className="font-medium">4,520</p>
                    </div>
                    <div>
                        <p className="text-muted-foreground">Detection</p>
                        <p className="font-medium">AI + Manual</p>
                    </div>
                </div>

                <div className="mt-4 p-3 bg-muted/50 rounded-lg flex items-start gap-2">
                    <Info className="w-4 h-4 text-forest mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-muted-foreground">
                        Drag the slider to compare pit stage with current sapling growth.
                        Enable AI overlay to see detection results.
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}

// Main Temporal Comparison Page
export default function TemporalComparisonPage() {
    const [showOverlay, setShowOverlay] = useState(true);
    const [overlayOpacity, setOverlayOpacity] = useState(70);
    const [selectedStage, setSelectedStage] = useState('op1');
    const [viewMode, setViewMode] = useState('slider');

    const stageData = {
        op1: { label: 'OP1 (Pit Stage)', date: 'March 15, 2024' },
        op2: { label: 'OP2 (Initial Growth)', date: 'June 20, 2024' },
        op3: { label: 'OP3 (Sapling Stage)', date: 'October 20, 2024' },
    };

    const currentStage = stageData[selectedStage as keyof typeof stageData] || stageData.op1;

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
                            <p className="text-xs text-muted-foreground">Patch KL-042</p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm">
                        <Calendar className="w-4 h-4 mr-2" />
                        Select Dates
                    </Button>
                </div>
            </header>

            {/* Main Content */}
            <div className="flex-1 flex">
                {/* Comparison View */}
                <div className="flex-1 flex flex-col">
                    {/* Timeline */}
                    <TimelineSelector selectedStage={selectedStage} onSelectStage={setSelectedStage} />

                    {/* Comparison Slider */}
                    <div className="flex-1 relative">
                        {viewMode === 'slider' && (
                            <ComparisonSlider
                                leftLabel={currentStage.label}
                                rightLabel="OP3 (Sapling Stage)"
                                leftDate={currentStage.date}
                                rightDate="October 20, 2024"
                                showOverlay={showOverlay}
                                overlayOpacity={overlayOpacity}
                            />
                        )}

                        {viewMode === 'side-by-side' && (
                            <div className="flex h-full">
                                <div className="flex-1 bg-gradient-to-br from-earth/20 to-earth/40 relative">
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="text-center">
                                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-earth/30 flex items-center justify-center">
                                                <div className="w-8 h-8 rounded-full border-2 border-dashed border-earth/50" />
                                            </div>
                                            <p className="font-semibold text-sm">{currentStage.label}</p>
                                            <p className="text-xs text-muted-foreground">{currentStage.date}</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="w-px bg-border" />
                                <div className="flex-1 bg-gradient-to-br from-forest/20 to-alive/30 relative">
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <div className="text-center">
                                            <TreePine className="w-16 h-16 mx-auto mb-4 text-alive/70" />
                                            <p className="font-semibold text-sm">OP3 (Sapling Stage)</p>
                                            <p className="text-xs text-muted-foreground">October 20, 2024</p>
                                        </div>
                                    </div>
                                    {/* AI Overlay */}
                                    {showOverlay && (
                                        <div className="absolute inset-0" style={{ opacity: overlayOpacity / 100 }}>
                                            {mockOverlayData.map((sapling) => (
                                                <div
                                                    key={sapling.id}
                                                    className={`absolute w-5 h-5 rounded-full flex items-center justify-center ${sapling.status === 'alive' ? 'bg-alive/80' : 'bg-dead/80'
                                                        }`}
                                                    style={{ left: `${sapling.x}%`, top: `${sapling.y}%` }}
                                                >
                                                    {sapling.status === 'alive' ? (
                                                        <CheckCircle2 className="w-3 h-3 text-white" />
                                                    ) : (
                                                        <XCircle className="w-3 h-3 text-white" />
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {viewMode === 'overlay' && (
                            <div className="h-full bg-gradient-to-br from-forest/20 to-alive/30 relative">
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="text-center">
                                        <TreePine className="w-16 h-16 mx-auto mb-4 text-alive/70" />
                                        <p className="font-semibold text-sm">OP3 (Sapling Stage)</p>
                                        <p className="text-xs text-muted-foreground">October 20, 2024</p>
                                    </div>
                                </div>
                                {/* AI Overlay */}
                                {showOverlay && (
                                    <div className="absolute inset-0" style={{ opacity: overlayOpacity / 100 }}>
                                        {mockOverlayData.map((sapling) => (
                                            <motion.div
                                                key={sapling.id}
                                                initial={{ scale: 0 }}
                                                animate={{ scale: 1 }}
                                                transition={{ delay: sapling.id * 0.02 }}
                                                className={`absolute w-6 h-6 rounded-full flex items-center justify-center ${sapling.status === 'alive' ? 'bg-alive/80' : 'bg-dead/80'
                                                    }`}
                                                style={{ left: `${sapling.x}%`, top: `${sapling.y}%` }}
                                            >
                                                {sapling.status === 'alive' ? (
                                                    <CheckCircle2 className="w-4 h-4 text-white" />
                                                ) : (
                                                    <XCircle className="w-4 h-4 text-white" />
                                                )}
                                            </motion.div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
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
                    <PatchInfoCard />

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
                                <span className="font-semibold text-alive">3,941 (87.2%)</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-dead" />
                                    <span className="text-sm">Dead</span>
                                </div>
                                <span className="font-semibold text-dead">579 (12.8%)</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full bg-uncertain" />
                                    <span className="text-sm">Uncertain</span>
                                </div>
                                <span className="font-semibold text-uncertain">0 (0%)</span>
                            </div>

                            <div className="pt-4 border-t border-border">
                                <div className="flex items-center justify-between text-sm">
                                    <span className="text-muted-foreground">Avg. Confidence</span>
                                    <span className="font-semibold">94.2%</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Actions */}
                    <div className="mt-4 space-y-2">
                        <Button className="w-full gradient-forest text-white border-0">
                            <Download className="w-4 h-4 mr-2" />
                            Export Comparison
                        </Button>
                        <Link href="/dashboard/analytics" className="block">
                            <Button variant="outline" className="w-full">
                                View Analytics
                            </Button>
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
