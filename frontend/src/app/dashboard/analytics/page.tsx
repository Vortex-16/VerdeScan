'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ArrowLeft,
    BarChart3,
    TrendingUp,
    TrendingDown,
    Download,
    FileText,
    Calendar,
    Filter,
    RefreshCw,
    AlertTriangle,
    ChevronRight,
    PieChart,
    Activity,
    Leaf,
    Home,
    Map,
    Layers,
    Settings,
    Menu,
    X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';

// Mock data
const survivalTrendData = [
    { year: '2024 Q1', value: 95, label: 'Mar 2024' },
    { year: '2024 Q2', value: 92, label: 'Jun 2024' },
    { year: '2024 Q3', value: 89, label: 'Sep 2024' },
    { year: '2024 Q4', value: 87, label: 'Dec 2024' },
];

const districtData = [
    { name: 'Khordha', survival: 89, patches: 42, status: 'healthy' },
    { name: 'Cuttack', survival: 82, patches: 38, status: 'healthy' },
    { name: 'Puri', survival: 75, patches: 31, status: 'warning' },
    { name: 'Mayurbhanj', survival: 71, patches: 45, status: 'warning' },
    { name: 'Angul', survival: 68, patches: 28, status: 'critical' },
    { name: 'Jajpur', survival: 65, patches: 22, status: 'critical' },
];

const alertPatches = [
    { id: 'MN-018', district: 'Mayurbhanj', survival: 62.5, delta: -8.2 },
    { id: 'JK-042', district: 'Jajpur', survival: 68.2, delta: -5.1 },
    { id: 'AB-091', district: 'Angul', survival: 69.4, delta: -4.8 },
    { id: 'PQ-156', district: 'Puri', survival: 71.2, delta: -3.2 },
];

// Counter hook
function useCounter(target: number, duration: number = 1500) {
    const [count, setCount] = useState(0);
    const ref = useRef<HTMLSpanElement>(null);
    const hasAnimated = useRef(false);

    useEffect(() => {
        if (hasAnimated.current) return;

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && !hasAnimated.current) {
                    hasAnimated.current = true;
                    const startTime = Date.now();
                    const animate = () => {
                        const elapsed = Date.now() - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const eased = 1 - Math.pow(1 - progress, 3);
                        setCount(Math.floor(eased * target));
                        if (progress < 1) {
                            requestAnimationFrame(animate);
                        }
                    };
                    animate();
                }
            },
            { threshold: 0.5 }
        );

        if (ref.current) {
            observer.observe(ref.current);
        }

        return () => observer.disconnect();
    }, [target, duration]);

    return { count, ref };
}

// Survival Trend Chart (Simplified visual)
function SurvivalTrendChart() {
    const maxValue = 100;
    const minValue = 60;
    const threshold = 85;

    return (
        <Card className="glass-card">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-medium flex items-center gap-2">
                        <Activity className="w-5 h-5 text-forest" />
                        Survival Trend
                    </CardTitle>
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm">
                            <RefreshCw className="w-4 h-4" />
                        </Button>
                        <select className="text-sm bg-muted rounded-lg px-3 py-1.5 border-0 focus:ring-2 focus:ring-forest/50">
                            <option>Last 12 Months</option>
                            <option>Last 6 Months</option>
                            <option>Year to Date</option>
                        </select>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="h-64 relative">
                    {/* Chart grid */}
                    <div className="absolute inset-0 flex flex-col justify-between border-l border-b border-border">
                        {[100, 90, 80, 70, 60].map((value) => (
                            <div key={value} className="flex items-center gap-2 relative">
                                <span className="absolute -left-8 text-xs text-muted-foreground">{value}%</span>
                                <div className="flex-1 border-t border-dashed border-border/50" />
                            </div>
                        ))}
                    </div>

                    {/* Threshold line */}
                    <div
                        className="absolute left-0 right-0 border-t-2 border-dashed border-forest/50 z-10"
                        style={{ top: `${((maxValue - threshold) / (maxValue - minValue)) * 100}%` }}
                    >
                        <span className="absolute right-0 -top-5 text-xs text-forest font-medium">85% Target</span>
                    </div>

                    {/* Data line and points */}
                    <svg className="absolute inset-0 overflow-visible" style={{ marginLeft: '20px' }}>
                        <defs>
                            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stopColor="var(--forest)" />
                                <stop offset="100%" stopColor="var(--forest-light)" />
                            </linearGradient>
                        </defs>

                        {/* Line */}
                        <motion.path
                            initial={{ pathLength: 0 }}
                            animate={{ pathLength: 1 }}
                            transition={{ duration: 1.5, ease: "easeInOut" }}
                            d={survivalTrendData.map((d, i) => {
                                const x = (i / (survivalTrendData.length - 1)) * 90 + 5;
                                const y = ((maxValue - d.value) / (maxValue - minValue)) * 100;
                                return `${i === 0 ? 'M' : 'L'} ${x}% ${y}%`;
                            }).join(' ')}
                            fill="none"
                            stroke="url(#lineGradient)"
                            strokeWidth="3"
                            strokeLinecap="round"
                            className="filter drop-shadow-lg"
                        />

                        {/* Points */}
                        {survivalTrendData.map((d, i) => {
                            const x = (i / (survivalTrendData.length - 1)) * 90 + 5;
                            const y = ((maxValue - d.value) / (maxValue - minValue)) * 100;
                            return (
                                <motion.g key={i} initial={{ opacity: 0, scale: 0 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.5 + i * 0.1 }}>
                                    <circle cx={`${x}%`} cy={`${y}%`} r="8" fill="white" className="drop-shadow-md" />
                                    <circle cx={`${x}%`} cy={`${y}%`} r="5" fill="var(--forest)" />
                                </motion.g>
                            );
                        })}
                    </svg>

                    {/* X-axis labels */}
                    <div className="absolute bottom-0 left-0 right-0 flex justify-between px-4 translate-y-6 ml-5">
                        {survivalTrendData.map((d, i) => (
                            <span key={i} className="text-xs text-muted-foreground">{d.label}</span>
                        ))}
                    </div>
                </div>

                {/* Legend */}
                <div className="flex items-center justify-center gap-6 mt-8 pt-4 border-t border-border">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-forest" />
                        <span className="text-sm text-muted-foreground">Survival Rate</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-0 border-t-2 border-dashed border-forest/50" />
                        <span className="text-sm text-muted-foreground">Target (85%)</span>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

// District Comparison Chart
function DistrictComparisonChart() {
    return (
        <Card className="glass-card">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-medium flex items-center gap-2">
                        <BarChart3 className="w-5 h-5 text-forest" />
                        Survival by District
                    </CardTitle>
                    <Link href="#" className="text-sm text-forest hover:text-forest-light transition-colors flex items-center gap-1">
                        View All
                        <ChevronRight className="w-4 h-4" />
                    </Link>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {districtData.map((district, index) => (
                    <motion.div
                        key={district.name}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="space-y-2"
                    >
                        <div className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                                <span className="font-medium">{district.name}</span>
                                <Badge variant="secondary" className="text-xs">
                                    {district.patches} patches
                                </Badge>
                            </div>
                            <span className={`font-semibold ${district.status === 'critical' ? 'text-dead' :
                                    district.status === 'warning' ? 'text-uncertain' :
                                        'text-alive'
                                }`}>
                                {district.survival}%
                            </span>
                        </div>
                        <div className="relative h-3 bg-muted rounded-full overflow-hidden">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${district.survival}%` }}
                                transition={{ duration: 1, delay: 0.5 + index * 0.1, ease: [0.16, 1, 0.3, 1] }}
                                className={`absolute inset-y-0 left-0 rounded-full ${district.status === 'critical' ? 'bg-dead' :
                                        district.status === 'warning' ? 'bg-uncertain' :
                                            'bg-alive'
                                    }`}
                            />
                            {/* Threshold marker */}
                            <div className="absolute inset-y-0 left-[85%] w-0.5 bg-forest/30" />
                        </div>
                    </motion.div>
                ))}
            </CardContent>
        </Card>
    );
}

// Patches Below Threshold
function PatchesBelowThreshold() {
    return (
        <Card className="glass-card">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-medium flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-dead" />
                        Patches Below Threshold
                    </CardTitle>
                    <Badge variant="secondary" className="bg-dead/10 text-dead border-0">
                        {alertPatches.length} patches
                    </Badge>
                </div>
            </CardHeader>
            <CardContent className="space-y-3">
                {alertPatches.map((patch, index) => (
                    <motion.div
                        key={patch.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center justify-between p-3 bg-dead/5 rounded-lg hover:bg-dead/10 transition-colors cursor-pointer group"
                    >
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="font-medium">{patch.id}</span>
                                <span className="text-xs text-muted-foreground">• {patch.district}</span>
                            </div>
                            <p className="text-sm text-dead font-medium">{patch.survival}%</p>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="text-right">
                                <div className="flex items-center gap-1 text-dead text-sm">
                                    <TrendingDown className="w-4 h-4" />
                                    {patch.delta}%
                                </div>
                                <span className="text-xs text-muted-foreground">vs last month</span>
                            </div>
                            <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-forest transition-colors" />
                        </div>
                    </motion.div>
                ))}

                <Link href="/dashboard/explorer">
                    <Button variant="outline" className="w-full mt-2">
                        View All {alertPatches.length} Patches
                    </Button>
                </Link>
            </CardContent>
        </Card>
    );
}

// Report Generator
function ReportGenerator() {
    const [reportType, setReportType] = useState('state');
    const [format, setFormat] = useState('pdf');
    const [includeOptions, setIncludeOptions] = useState({
        summary: true,
        patchDetails: true,
        charts: true,
        confidence: false,
        rawData: false,
        coordinates: false,
    });

    return (
        <Card className="glass-card">
            <CardHeader>
                <CardTitle className="text-lg font-medium flex items-center gap-2">
                    <FileText className="w-5 h-5 text-forest" />
                    Report Generation
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Report Type */}
                <div>
                    <label className="text-sm font-medium mb-2 block">Report Type</label>
                    <div className="flex gap-2">
                        {[
                            { id: 'state', label: 'State Summary' },
                            { id: 'district', label: 'District' },
                            { id: 'patch', label: 'Patch-Level' },
                        ].map((type) => (
                            <button
                                key={type.id}
                                onClick={() => setReportType(type.id)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${reportType === type.id
                                        ? 'bg-forest text-white'
                                        : 'bg-muted hover:bg-muted/80'
                                    }`}
                            >
                                {type.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Date Range */}
                <div>
                    <label className="text-sm font-medium mb-2 block">Date Range</label>
                    <div className="flex gap-2">
                        <div className="flex-1 relative">
                            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <input
                                type="date"
                                defaultValue="2024-01-01"
                                className="w-full h-10 pl-10 pr-4 bg-muted rounded-lg border-0 focus:ring-2 focus:ring-forest/50 text-sm"
                            />
                        </div>
                        <span className="flex items-center text-muted-foreground">to</span>
                        <div className="flex-1 relative">
                            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <input
                                type="date"
                                defaultValue="2024-12-31"
                                className="w-full h-10 pl-10 pr-4 bg-muted rounded-lg border-0 focus:ring-2 focus:ring-forest/50 text-sm"
                            />
                        </div>
                    </div>
                </div>

                {/* Format */}
                <div>
                    <label className="text-sm font-medium mb-2 block">Format</label>
                    <div className="flex gap-2">
                        {['pdf', 'csv', 'excel'].map((f) => (
                            <button
                                key={f}
                                onClick={() => setFormat(f)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium uppercase transition-all ${format === f
                                        ? 'bg-forest text-white'
                                        : 'bg-muted hover:bg-muted/80'
                                    }`}
                            >
                                {f}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Include Options */}
                <div>
                    <label className="text-sm font-medium mb-3 block">Include in Report</label>
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            { id: 'summary', label: 'Executive Summary' },
                            { id: 'patchDetails', label: 'Patch Details' },
                            { id: 'charts', label: 'Trend Charts' },
                            { id: 'confidence', label: 'AI Confidence' },
                            { id: 'rawData', label: 'Raw Sapling Data' },
                            { id: 'coordinates', label: 'Coordinates' },
                        ].map((option) => (
                            <label key={option.id} className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={includeOptions[option.id as keyof typeof includeOptions]}
                                    onChange={(e) => setIncludeOptions({ ...includeOptions, [option.id]: e.target.checked })}
                                    className="w-4 h-4 rounded text-forest focus:ring-forest"
                                />
                                <span className="text-sm">{option.label}</span>
                            </label>
                        ))}
                    </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-4 border-t border-border">
                    <Button variant="outline" className="flex-1">
                        Preview
                    </Button>
                    <Button className="flex-1 gradient-forest text-white border-0">
                        <Download className="w-4 h-4 mr-2" />
                        Generate Report
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}

// Sidebar Navigation
function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const links = [
        { icon: Home, label: 'Dashboard', href: '/dashboard' },
        { icon: Map, label: 'Patch Explorer', href: '/dashboard/explorer' },
        { icon: Layers, label: 'Temporal View', href: '/dashboard/temporal' },
        { icon: BarChart3, label: 'Analytics', href: '/dashboard/analytics', active: true },
        { icon: FileText, label: 'Reports', href: '/dashboard/reports' },
        { icon: Settings, label: 'Settings', href: '/dashboard/settings' },
    ];

    return (
        <>
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    />
                )}
            </AnimatePresence>

            <motion.aside
                initial={{ x: -300 }}
                animate={{ x: isOpen ? 0 : -300 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className="fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-50 lg:translate-x-0 lg:z-30"
            >
                <div className="flex flex-col h-full">
                    <div className="h-16 flex items-center justify-between px-4 border-b border-border">
                        <Link href="/" className="flex items-center gap-2">
                            <div className="w-10 h-10 rounded-xl gradient-forest flex items-center justify-center">
                                <Leaf className="w-6 h-6 text-white" />
                            </div>
                            <span className="text-xl font-bold text-gradient">VerdeScan</span>
                        </Link>
                        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onClose}>
                            <X className="w-5 h-5" />
                        </Button>
                    </div>

                    <nav className="flex-1 p-4 space-y-1">
                        {links.map((link) => (
                            <Link
                                key={link.label}
                                href={link.href}
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${link.active
                                        ? 'bg-forest text-white'
                                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                                    }`}
                            >
                                <link.icon className={`w-5 h-5 ${link.active ? '' : 'group-hover:scale-110'} transition-transform`} />
                                <span className="font-medium">{link.label}</span>
                            </Link>
                        ))}
                    </nav>
                </div>
            </motion.aside>
        </>
    );
}

// Main Analytics Page
export default function AnalyticsPage() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const survivalRate = useCounter(871, 1500);
    const totalPatches = useCounter(247, 1500);
    const belowThreshold = useCounter(12, 1500);

    return (
        <div className="min-h-screen bg-background">
            <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

            <div className="lg:pl-64">
                {/* Header */}
                <header className="sticky top-0 z-30 h-16 glass border-b border-border">
                    <div className="flex items-center justify-between h-full px-4 lg:px-8">
                        <div className="flex items-center gap-4">
                            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
                                <Menu className="w-5 h-5" />
                            </Button>
                            <div>
                                <h1 className="font-semibold">Analytics & Reports</h1>
                                <p className="text-xs text-muted-foreground">Afforestation performance insights</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm">
                                <Filter className="w-4 h-4 mr-2" />
                                Filters
                            </Button>
                            <Button variant="outline" size="sm">
                                <Download className="w-4 h-4 mr-2" />
                                Export
                            </Button>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="p-4 lg:p-8">
                    {/* Quick Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5 }}
                        >
                            <Card className="glass-card">
                                <CardContent className="p-6 flex items-center gap-4">
                                    <div className="w-14 h-14 rounded-xl bg-forest/10 flex items-center justify-center">
                                        <TrendingUp className="w-7 h-7 text-forest" />
                                    </div>
                                    <div>
                                        <p className="text-3xl font-bold">
                                            <span ref={survivalRate.ref}>{(survivalRate.count / 10).toFixed(1)}</span>%
                                        </p>
                                        <p className="text-sm text-muted-foreground">Overall Survival</p>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.1 }}
                        >
                            <Card className="glass-card">
                                <CardContent className="p-6 flex items-center gap-4">
                                    <div className="w-14 h-14 rounded-xl bg-alive/10 flex items-center justify-center">
                                        <PieChart className="w-7 h-7 text-alive" />
                                    </div>
                                    <div>
                                        <p className="text-3xl font-bold">
                                            <span ref={totalPatches.ref}>{totalPatches.count}</span>
                                        </p>
                                        <p className="text-sm text-muted-foreground">Patches Analyzed</p>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.2 }}
                        >
                            <Card className="glass-card">
                                <CardContent className="p-6 flex items-center gap-4">
                                    <div className="w-14 h-14 rounded-xl bg-dead/10 flex items-center justify-center">
                                        <AlertTriangle className="w-7 h-7 text-dead" />
                                    </div>
                                    <div>
                                        <p className="text-3xl font-bold">
                                            <span ref={belowThreshold.ref}>{belowThreshold.count}</span>
                                        </p>
                                        <p className="text-sm text-muted-foreground">Below Threshold</p>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    </div>

                    {/* Charts Row */}
                    <div className="grid lg:grid-cols-2 gap-6 mb-8">
                        <SurvivalTrendChart />
                        <DistrictComparisonChart />
                    </div>

                    {/* Bottom Row */}
                    <div className="grid lg:grid-cols-2 gap-6">
                        <PatchesBelowThreshold />
                        <ReportGenerator />
                    </div>
                </main>
            </div>
        </div>
    );
}
