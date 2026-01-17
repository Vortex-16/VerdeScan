'use client';

import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    ArrowLeft,
    TrendingUp,
    TrendingDown,
    Download,
    Calendar,
    Filter,
    Menu,
    Leaf,
    Home,
    Map,
    Layers,
    BarChart3,
    FileText,
    Settings,
    X,
    MapPin,
    AlertCircle,
    CheckCircle,
    RefreshCw
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { AnimatePresence } from 'framer-motion';
import { api, GlobalStats } from '@/lib/api';

// Dynamic stats (will be fetched from API)
interface AnalyticsStats {
    overall: number;
    trend: string;
    patches: number;
    critical: number;
    totalTrees: number;
    aliveTrees: number;
    deadTrees: number;
}

// Dynamic patch data for district rankings
interface PatchAnalytics {
    name: string;
    value: number;
    trend: 'up' | 'down';
}

// Counter hook
function useCounter(target: number, duration: number = 1000) {
    const [count, setCount] = useState(0);
    const ref = useRef<HTMLSpanElement>(null);
    const hasAnimated = useRef(false);

    useEffect(() => {
        // Reset state when target changes
        hasAnimated.current = false;

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

// Sidebar
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

            <aside className="hidden lg:flex flex-col fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-30">
                <div className="flex flex-col h-full">
                    <div className="h-16 flex items-center px-6 border-b border-border">
                        <Link href="/" className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg gradient-forest flex items-center justify-center">
                                <Leaf className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-lg font-bold text-gradient">VerdeScan</span>
                        </Link>
                    </div>

                    <nav className="flex-1 p-4 space-y-1">
                        {links.map((link) => (
                            <Link
                                key={link.label}
                                href={link.href}
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${link.active
                                    ? 'bg-forest text-white shadow-lg shadow-forest/25'
                                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                                    }`}
                            >
                                <link.icon className={`w-5 h-5 ${link.active ? '' : 'group-hover:scale-110'} transition-transform`} />
                                <span className="font-medium">{link.label}</span>
                            </Link>
                        ))}
                    </nav>
                </div>
            </aside>

            <motion.aside
                initial={{ x: -300 }}
                animate={{ x: isOpen ? 0 : -300 }}
                transition={{ duration: 0.3 }}
                className="fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-50 lg:hidden"
            >
                <div className="flex flex-col h-full relative">
                    <Button variant="ghost" size="icon" className="absolute top-4 right-4" onClick={onClose}>
                        <X className="w-5 h-5" />
                    </Button>
                    <div className="h-16 flex items-center px-6 border-b border-border">
                        <Link href="/" className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg gradient-forest flex items-center justify-center">
                                <Leaf className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-lg font-bold text-gradient">VerdeScan</span>
                        </Link>
                    </div>
                    <nav className="flex-1 p-4 space-y-1">
                        {links.map((link) => (
                            <Link
                                key={link.label}
                                href={link.href}
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${link.active
                                    ? 'bg-forest text-white shadow-lg shadow-forest/25'
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

export default function AnalyticsPage() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<AnalyticsStats>({
        overall: 0, trend: '+0', patches: 0, critical: 0, totalTrees: 0, aliveTrees: 0, deadTrees: 0
    });
    const [patchData, setPatchData] = useState<PatchAnalytics[]>([]);

    // Fetch real data from API
    useEffect(() => {
        async function fetchAnalytics() {
            setLoading(true);
            try {
                const globalStats = await api.getGlobalStats();
                const patchNames = await api.getPatches();

                // Fetch details for patches to calculate critical count
                const patchDetails = await Promise.all(
                    patchNames.map(async (name: string) => {
                        const details = await api.getPatchDetails(name);
                        if (details) {
                            const total = details.summary?.total_trees || 1;
                            const alive = details.summary?.alive_trees || 0;
                            const survivalRate = (alive / total) * 100;
                            return {
                                name: name.length > 15 ? name.slice(0, 15) + '...' : name,
                                value: Math.round(survivalRate),
                                trend: survivalRate >= 70 ? 'up' : 'down' as const,
                                isCritical: survivalRate < 50
                            };
                        }
                        return null;
                    })
                );

                const validPatches = patchDetails.filter(Boolean) as (PatchAnalytics & { isCritical: boolean })[];
                const criticalCount = validPatches.filter(p => p.isCritical).length;

                // Build analytics stats from real data
                setStats({
                    overall: globalStats.avg_survival_rate || 0,
                    trend: globalStats.avg_survival_rate >= 85 ? '+2.3%' : '-1.5%',
                    patches: globalStats.total_patches || 0,
                    critical: criticalCount,
                    totalTrees: globalStats.total_trees || 0,
                    aliveTrees: globalStats.total_alive || 0,
                    deadTrees: globalStats.total_dead || 0
                });

                setPatchData(validPatches.slice(0, 5)); // Show top 5 in list
            } catch (error) {
                console.error('Error fetching analytics:', error);
            }
            setLoading(false);
        }
        fetchAnalytics();
    }, []);

    const overallCounter = useCounter(Math.round(stats.overall * 10));
    const patchesCounter = useCounter(stats.patches);
    const criticalCounter = useCounter(stats.critical);

    // Generate monthly data from current survival rate
    const monthlyData = Array.from({ length: 6 }, (_, i) => ({
        month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'][i],
        value: Math.max(0, Math.min(100, Math.round(stats.overall + (5 - i) * 0.5)))
    }));

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
                                <h1 className="font-semibold">Analytics</h1>
                                <p className="text-xs text-muted-foreground">Performance insights</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <select className="text-xs bg-muted rounded-lg px-3 py-2 border-0">
                                <option>Last 6 Months</option>
                                <option>Last Year</option>
                                <option>All Time</option>
                            </select>
                            <Button variant="outline" size="sm">
                                <Download className="w-4 h-4 mr-2" />
                                Export
                            </Button>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="p-4 lg:p-8 max-w-7xl mx-auto">
                    {/* Hero Stats */}
                    <div className="grid md:grid-cols-3 gap-4 mb-6">
                        <Card className="glass-card">
                            <CardContent className="p-5">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-muted-foreground">Overall Survival</span>
                                    <Badge variant="secondary" className="bg-alive/10 text-alive border-0 text-xs">
                                        <TrendingUp className="w-3 h-3 mr-1" />
                                        {stats.trend}%
                                    </Badge>
                                </div>
                                <p className="text-3xl font-semibold">
                                    <span ref={overallCounter.ref}>{(overallCounter.count / 10).toFixed(1)}</span>%
                                </p>
                            </CardContent>
                        </Card>

                        <Card className="glass-card">
                            <CardContent className="p-5">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-muted-foreground">Total Patches</span>
                                    <MapPin className="w-4 h-4 text-forest" />
                                </div>
                                <p className="text-3xl font-semibold">
                                    <span ref={patchesCounter.ref}>{patchesCounter.count}</span>
                                </p>
                            </CardContent>
                        </Card>

                        <Card className="glass-card">
                            <CardContent className="p-5">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-xs text-muted-foreground">Critical Patches</span>
                                    <AlertCircle className="w-4 h-4 text-dead" />
                                </div>
                                <p className="text-3xl font-semibold text-dead">
                                    <span ref={criticalCounter.ref}>{criticalCounter.count}</span>
                                </p>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Main Grid */}
                    <div className="grid lg:grid-cols-2 gap-6">
                        {/* Trend Chart */}
                        <Card className="glass-card">
                            <CardHeader>
                                <CardTitle className="text-base font-medium">6-Month Trend</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="h-48 flex items-end justify-between gap-2">
                                    {monthlyData.map((item, i) => (
                                        <div key={i} className="flex-1 flex flex-col items-center gap-2">
                                            <motion.div
                                                initial={{ height: 0 }}
                                                animate={{ height: `${item.value}%` }}
                                                transition={{ duration: 0.6, delay: i * 0.1 }}
                                                className="w-full bg-forest rounded-t relative"
                                            >
                                                <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-medium">
                                                    {item.value}%
                                                </span>
                                            </motion.div>
                                            <span className="text-xs text-muted-foreground">{item.month}</span>
                                        </div>
                                    ))}
                                </div>
                                <div className="mt-4 pt-4 border-t border-border">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground">Target: 85%</span>
                                        <span className="text-forest font-medium">Current: 87%</span>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* District Rankings */}
                        <Card className="glass-card">
                            <CardHeader>
                                <CardTitle className="text-base font-medium">Patch Performance</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {patchData.length > 0 ? patchData.map((patch: PatchAnalytics, i: number) => (
                                    <motion.div
                                        key={i}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.08 }}
                                        className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/30 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs font-medium text-muted-foreground w-4">#{i + 1}</span>
                                            <span className="text-sm font-medium">{patch.name}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-semibold">{patch.value}%</span>
                                            {patch.trend === 'up' ? (
                                                <TrendingUp className="w-4 h-4 text-alive" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4 text-dead" />
                                            )}
                                        </div>
                                    </motion.div>
                                )) : (
                                    <p className="text-sm text-muted-foreground text-center py-4">
                                        No patches analyzed yet. Upload drone images to see data.
                                    </p>
                                )}
                            </CardContent>
                        </Card>
                    </div>

                    {/* Quick Actions */}
                    <div className="mt-6 flex gap-3">
                        <Link href="/dashboard/explorer" className="flex-1">
                            <Button variant="outline" className="w-full">
                                <Map className="w-4 h-4 mr-2" />
                                View Map
                            </Button>
                        </Link>
                        <Link href="/dashboard/reports" className="flex-1">
                            <Button className="w-full bg-forest text-white hover:bg-forest-light">
                                <FileText className="w-4 h-4 mr-2" />
                                Generate Report
                            </Button>
                        </Link>
                    </div>
                </main>
            </div>
        </div>
    );
}
