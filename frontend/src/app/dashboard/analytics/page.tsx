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
    CheckCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { AnimatePresence } from 'framer-motion';

// Mock data
const stats = {
    overall: 87.1,
    trend: '+2.3',
    patches: 247,
    critical: 12
};

const districtData = [
    { name: 'Khordha', value: 89, trend: 'up' },
    { name: 'Cuttack', value: 82, trend: 'up' },
    { name: 'Puri', value: 75, trend: 'down' },
    { name: 'Mayurbhanj', value: 71, trend: 'down' },
    { name: 'Angul', value: 68, trend: 'down' },
];

const monthlyData = [
    { month: 'Jan', value: 92 },
    { month: 'Feb', value: 90 },
    { month: 'Mar', value: 89 },
    { month: 'Apr', value: 88 },
    { month: 'May', value: 87 },
    { month: 'Jun', value: 87 },
];

// Counter hook
function useCounter(target: number, duration: number = 1000) {
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
    const overallCounter = useCounter(871);
    const patchesCounter = useCounter(247);
    const criticalCounter = useCounter(12);

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
                                <CardTitle className="text-base font-medium">District Performance</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {districtData.map((district, i) => (
                                    <motion.div
                                        key={i}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.08 }}
                                        className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/30 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs font-medium text-muted-foreground w-4">#{i + 1}</span>
                                            <span className="text-sm font-medium">{district.name}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-semibold">{district.value}%</span>
                                            {district.trend === 'up' ? (
                                                <TrendingUp className="w-4 h-4 text-alive" />
                                            ) : (
                                                <TrendingDown className="w-4 h-4 text-dead" />
                                            )}
                                        </div>
                                    </motion.div>
                                ))}
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
