'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { gsap } from 'gsap';
import {
    TreePine,
    Leaf,
    Map,
    BarChart3,
    Bell,
    Search,
    Calendar,
    Download,
    ChevronRight,
    TrendingUp,
    TrendingDown,
    AlertTriangle,
    CheckCircle2,
    XCircle,
    HelpCircle,
    Eye,
    MapPin,
    Clock,
    Settings,
    Menu,
    X,
    ChevronDown,
    ArrowUpRight,
    Layers,
    FileText,
    Home
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';

// Mock data
const mockStats = {
    totalPatches: 247,
    totalPlanted: 12400000,
    totalAlive: 10788000,
    totalDead: 1612000,
    survivalRate: 87.1,
    yearProgress: {
        year1: 100,
        year2: 75,
        year3: 25
    }
};

const alertPatches = [
    { id: 'MN-018', location: 'Zone 3, Sector B', survival: 62.5, status: 'critical', lastSurvey: '2 days ago' },
    { id: 'JK-042', location: 'Zone 5, Sector A', survival: 68.2, status: 'critical', lastSurvey: '5 days ago' },
    { id: 'AB-091', location: 'Zone 1, Sector C', survival: 71.4, status: 'warning', lastSurvey: '1 week ago' },
    { id: 'PQ-156', location: 'Zone 4, Sector D', survival: 74.8, status: 'warning', lastSurvey: '3 days ago' },
    { id: 'KL-042', location: 'Zone 2, Sector A', survival: 87.2, status: 'healthy', lastSurvey: '1 day ago' },
];

// Reusable counter hook
function useCounter(target: number, duration: number = 2000) {
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

// Format large numbers (Indian format: Cr, Lakh)
function formatNumber(num: number): string {
    if (num >= 10000000) {
        return (num / 10000000).toFixed(2) + ' Cr';
    } else if (num >= 100000) {
        return (num / 100000).toFixed(0) + ' Lakh';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// KPI Card Component
function KPICard({
    icon: Icon,
    title,
    value,
    suffix = '',
    trend,
    trendValue,
    color,
    index
}: {
    icon: React.ElementType;
    title: string;
    value: number;
    suffix?: string;
    trend?: 'up' | 'down';
    trendValue?: string;
    color: string;
    index: number;
}) {
    const { count, ref } = useCounter(value);

    const colorClasses: Record<string, { bg: string; text: string; icon: string }> = {
        forest: { bg: 'bg-forest/10', text: 'text-forest', icon: 'text-forest' },
        alive: { bg: 'bg-alive/10', text: 'text-alive', icon: 'text-alive' },
        dead: { bg: 'bg-dead/10', text: 'text-dead', icon: 'text-dead' },
        earth: { bg: 'bg-earth/10', text: 'text-earth', icon: 'text-earth' },
    };

    const colors = colorClasses[color] || colorClasses.forest;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, delay: index * 0.1, ease: [0.16, 1, 0.3, 1] }}
        >
            <Card className="glass-card group hover:border-forest/30 transition-all duration-500 overflow-hidden relative">
                <div className="absolute inset-0 bg-gradient-to-br from-transparent to-forest/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <CardContent className="p-6 relative">
                    <div className="flex items-start justify-between mb-4">
                        <div className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
                            <Icon className={`w-6 h-6 ${colors.icon}`} />
                        </div>
                        {trend && (
                            <div className={`flex items-center gap-1 text-xs font-medium ${trend === 'up' ? 'text-alive' : 'text-dead'}`}>
                                {trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                {trendValue}
                            </div>
                        )}
                    </div>
                    <div className="space-y-1">
                        <p className="text-3xl font-bold">
                            <span ref={ref} className="counter-animate">{formatNumber(count)}</span>
                            <span className="text-xl text-muted-foreground ml-1">{suffix}</span>
                        </p>
                        <p className="text-sm text-muted-foreground">{title}</p>
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    );
}

// Survival Rate Gauge
function SurvivalGauge({ value }: { value: number }) {
    const [animatedValue, setAnimatedValue] = useState(0);

    useEffect(() => {
        const timer = setTimeout(() => {
            setAnimatedValue(value);
        }, 500);
        return () => clearTimeout(timer);
    }, [value]);

    const status = value >= 85 ? 'healthy' : value >= 70 ? 'warning' : 'critical';
    const statusConfig = {
        healthy: { label: 'Healthy', color: 'bg-alive', textColor: 'text-alive' },
        warning: { label: 'Needs Attention', color: 'bg-uncertain', textColor: 'text-uncertain' },
        critical: { label: 'Critical', color: 'bg-dead', textColor: 'text-dead' },
    };

    const config = statusConfig[status];

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
        >
            <Card className="glass-card">
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-medium">Overall Survival Rate</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-end justify-between mb-4">
                        <span className="text-5xl font-bold text-gradient">{animatedValue.toFixed(1)}%</span>
                        <Badge variant="secondary" className={`${config.color}/10 ${config.textColor} border-0`}>
                            <CheckCircle2 className="w-3 h-3 mr-1" />
                            {config.label}
                        </Badge>
                    </div>

                    <div className="relative h-3 bg-muted rounded-full overflow-hidden">
                        <motion.div
                            className={`absolute inset-y-0 left-0 ${config.color} rounded-full`}
                            initial={{ width: 0 }}
                            animate={{ width: `${animatedValue}%` }}
                            transition={{ duration: 1.5, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
                        />
                        {/* Threshold line at 85% */}
                        <div className="absolute inset-y-0 left-[85%] w-0.5 bg-forest/50" />
                    </div>

                    <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                        <span>0%</span>
                        <span className="text-forest">Target: 85%</span>
                        <span>100%</span>
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    );
}

// Year Progress Component
function YearProgress({ yearProgress }: { yearProgress: { year1: number; year2: number; year3: number } }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
        >
            <Card className="glass-card h-full">
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-medium">Monitoring Status</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {[
                        { label: 'Year 1 (2024)', value: yearProgress.year1, status: 'Completed' },
                        { label: 'Year 2 (2025)', value: yearProgress.year2, status: 'In Progress' },
                        { label: 'Year 3 (2026)', value: yearProgress.year3, status: 'In Progress' },
                    ].map((year, index) => (
                        <motion.div
                            key={year.label}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.4, delay: 0.5 + index * 0.1 }}
                            className="space-y-2"
                        >
                            <div className="flex items-center justify-between text-sm">
                                <span className="font-medium">{year.label}</span>
                                <span className="text-muted-foreground">{year.value}% - {year.status}</span>
                            </div>
                            <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                                <motion.div
                                    className={`absolute inset-y-0 left-0 rounded-full ${year.value === 100 ? 'bg-alive' : 'bg-forest'}`}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${year.value}%` }}
                                    transition={{ duration: 1, delay: 0.6 + index * 0.15, ease: [0.16, 1, 0.3, 1] }}
                                />
                            </div>
                        </motion.div>
                    ))}
                </CardContent>
            </Card>
        </motion.div>
    );
}

// Alert Patches Table
function AlertPatchesTable({ patches }: { patches: typeof alertPatches }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
        >
            <Card className="glass-card">
                <CardHeader className="pb-4">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-lg font-medium flex items-center gap-2">
                            <AlertTriangle className="w-5 h-5 text-uncertain" />
                            Patches Requiring Attention
                        </CardTitle>
                        <Button variant="ghost" size="sm" className="text-forest hover:text-forest-light">
                            View All
                            <ChevronRight className="w-4 h-4 ml-1" />
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-border">
                                    <th className="text-left py-3 px-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">Patch ID</th>
                                    <th className="text-left py-3 px-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">Location</th>
                                    <th className="text-left py-3 px-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">Survival</th>
                                    <th className="text-left py-3 px-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                                    <th className="text-left py-3 px-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">Last Survey</th>
                                    <th className="text-right py-3 px-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {patches.map((patch, index) => (
                                    <motion.tr
                                        key={patch.id}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ duration: 0.3, delay: 0.6 + index * 0.05 }}
                                        className={`border-b border-border/50 hover:bg-muted/30 transition-colors ${patch.status === 'critical' ? 'bg-dead/5' : ''}`}
                                    >
                                        <td className="py-3 px-2">
                                            <div className="flex items-center gap-2">
                                                {patch.status === 'critical' ? (
                                                    <XCircle className="w-4 h-4 text-dead" />
                                                ) : patch.status === 'warning' ? (
                                                    <AlertTriangle className="w-4 h-4 text-uncertain" />
                                                ) : (
                                                    <CheckCircle2 className="w-4 h-4 text-alive" />
                                                )}
                                                <span className="font-medium">{patch.id}</span>
                                            </div>
                                        </td>
                                        <td className="py-3 px-2 text-muted-foreground">{patch.location}</td>
                                        <td className="py-3 px-2">
                                            <div className="flex items-center gap-2">
                                                <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full ${patch.status === 'critical' ? 'bg-dead' : patch.status === 'warning' ? 'bg-uncertain' : 'bg-alive'}`}
                                                        style={{ width: `${patch.survival}%` }}
                                                    />
                                                </div>
                                                <span className={`text-sm font-medium ${patch.status === 'critical' ? 'text-dead' : patch.status === 'warning' ? 'text-uncertain' : 'text-alive'}`}>
                                                    {patch.survival}%
                                                </span>
                                            </div>
                                        </td>
                                        <td className="py-3 px-2">
                                            <Badge
                                                variant="secondary"
                                                className={`text-xs ${patch.status === 'critical' ? 'bg-dead/10 text-dead' :
                                                        patch.status === 'warning' ? 'bg-uncertain/10 text-uncertain' :
                                                            'bg-alive/10 text-alive'
                                                    }`}
                                            >
                                                {patch.status === 'critical' ? 'Critical' : patch.status === 'warning' ? 'Warning' : 'Healthy'}
                                            </Badge>
                                        </td>
                                        <td className="py-3 px-2 text-muted-foreground text-sm">{patch.lastSurvey}</td>
                                        <td className="py-3 px-2 text-right">
                                            <Button variant="ghost" size="sm" className="text-forest hover:text-forest-light">
                                                <Eye className="w-4 h-4 mr-1" />
                                                View
                                            </Button>
                                        </td>
                                    </motion.tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    );
}

// Sidebar Component
function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const links = [
        { icon: Home, label: 'Dashboard', href: '/dashboard', active: true },
        { icon: Map, label: 'Patch Explorer', href: '/dashboard/explorer' },
        { icon: Layers, label: 'Temporal View', href: '/dashboard/temporal' },
        { icon: BarChart3, label: 'Analytics', href: '/dashboard/analytics' },
        { icon: FileText, label: 'Reports', href: '/dashboard/reports' },
        { icon: Settings, label: 'Settings', href: '/dashboard/settings' },
    ];

    return (
        <>
            {/* Mobile overlay */}
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

            {/* Sidebar */}
            <motion.aside
                initial={{ x: -300 }}
                animate={{ x: isOpen ? 0 : -300 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className="fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-50 lg:translate-x-0 lg:z-30"
            >
                <div className="flex flex-col h-full">
                    {/* Logo */}
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

                    {/* Navigation */}
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

                    {/* User section */}
                    <div className="p-4 border-t border-border">
                        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-muted">
                            <div className="w-10 h-10 rounded-full bg-forest/20 flex items-center justify-center">
                                <span className="text-forest font-semibold">FO</span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">Forest Officer</p>
                                <p className="text-xs text-muted-foreground truncate">Khordha Division</p>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.aside>
        </>
    );
}

// Main Dashboard Component
export default function DashboardPage() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [selectedYear, setSelectedYear] = useState('2024');

    return (
        <div className="min-h-screen bg-background">
            {/* Sidebar */}
            <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

            {/* Main content */}
            <div className="lg:pl-64">
                {/* Top bar */}
                <header className="sticky top-0 z-30 h-16 glass border-b border-border">
                    <div className="flex items-center justify-between h-full px-4 lg:px-8">
                        <div className="flex items-center gap-4">
                            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(true)}>
                                <Menu className="w-5 h-5" />
                            </Button>
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                <input
                                    type="text"
                                    placeholder="Search patches, locations..."
                                    className="w-64 h-10 pl-10 pr-4 bg-muted/50 rounded-xl border-0 focus:ring-2 focus:ring-forest/50 focus:outline-none transition-all placeholder:text-muted-foreground"
                                />
                            </div>
                        </div>

                        <div className="flex items-center gap-3">
                            {/* Year selector */}
                            <div className="flex items-center gap-2 px-4 py-2 bg-muted/50 rounded-xl">
                                <Calendar className="w-4 h-4 text-muted-foreground" />
                                <select
                                    value={selectedYear}
                                    onChange={(e) => setSelectedYear(e.target.value)}
                                    className="bg-transparent border-0 text-sm font-medium focus:outline-none cursor-pointer"
                                >
                                    <option value="2024">Year: 2024</option>
                                    <option value="2025">Year: 2025</option>
                                    <option value="2026">Year: 2026</option>
                                </select>
                            </div>

                            {/* Notifications */}
                            <Button variant="ghost" size="icon" className="relative">
                                <Bell className="w-5 h-5" />
                                <span className="absolute top-2 right-2 w-2 h-2 bg-dead rounded-full" />
                            </Button>

                            {/* Download */}
                            <Button variant="ghost" size="icon">
                                <Download className="w-5 h-5" />
                            </Button>
                        </div>
                    </div>
                </header>

                {/* Dashboard content */}
                <main className="p-4 lg:p-8">
                    {/* Page header */}
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="mb-8"
                    >
                        <h1 className="text-3xl font-bold mb-2">Dashboard Overview</h1>
                        <p className="text-muted-foreground">
                            Monitor afforestation health across all patches in real-time
                        </p>
                    </motion.div>

                    {/* KPI Cards Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                        <KPICard
                            icon={MapPin}
                            title="Patches Monitored"
                            value={mockStats.totalPatches}
                            trend="up"
                            trendValue="+12%"
                            color="forest"
                            index={0}
                        />
                        <KPICard
                            icon={TreePine}
                            title="Saplings Planted"
                            value={mockStats.totalPlanted}
                            color="earth"
                            index={1}
                        />
                        <KPICard
                            icon={CheckCircle2}
                            title="Saplings Alive"
                            value={mockStats.totalAlive}
                            trend="up"
                            trendValue="+5.2%"
                            color="alive"
                            index={2}
                        />
                        <KPICard
                            icon={XCircle}
                            title="Saplings Dead"
                            value={mockStats.totalDead}
                            color="dead"
                            index={3}
                        />
                    </div>

                    {/* Survival Rate and Year Progress */}
                    <div className="grid lg:grid-cols-2 gap-4 mb-8">
                        <SurvivalGauge value={mockStats.survivalRate} />
                        <YearProgress yearProgress={mockStats.yearProgress} />
                    </div>

                    {/* Alert Patches Table */}
                    <AlertPatchesTable patches={alertPatches} />

                    {/* Quick Actions */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.7 }}
                        className="mt-8 flex flex-wrap gap-4"
                    >
                        <Link href="/dashboard/explorer">
                            <Button size="lg" className="btn-premium gradient-forest text-white border-0">
                                <Map className="w-5 h-5 mr-2" />
                                Open Patch Explorer
                                <ArrowUpRight className="w-4 h-4 ml-2" />
                            </Button>
                        </Link>
                        <Button size="lg" variant="outline">
                            <FileText className="w-5 h-5 mr-2" />
                            Generate Report
                        </Button>
                    </motion.div>
                </main>
            </div>
        </div>
    );
}
