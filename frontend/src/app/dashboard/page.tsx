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
import { api, GlobalStats } from '@/lib/api';

// Interface for patch alerts
interface PatchAlert {
    id: string;
    location: string;
    survival: number;
    status: 'critical' | 'warning' | 'healthy';
    lastSurvey: string;
}

// Reusable counter hook
function useCounter(target: number, duration: number = 2000) {
    const [count, setCount] = useState(0);
    const ref = useRef<HTMLSpanElement>(null);
    const hasAnimated = useRef(false);

    useEffect(() => {
        // Reset animation state when target changes
        hasAnimated.current = false;
        setCount(0);

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) {
                    hasAnimated.current = true;
                    const startTime = Date.now();
                    const animate = () => {
                        const elapsed = Date.now() - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const eased = 1 - Math.pow(1 - progress, 3);
                        setCount(Math.floor(eased * target));
                        if (progress < 1) {
                            requestAnimationFrame(animate);
                        } else {
                            setCount(target); // Ensure final value is exact
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
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: index * 0.08 }}
        >
            <Card className="glass-card">
                <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                        <div className={`w-11 h-11 rounded-lg ${colors.bg} flex items-center justify-center`}>
                            <Icon className={`w-5 h-5 ${colors.icon}`} />
                        </div>
                        {trend && (
                            <div className={`flex items-center gap-1 text-xs font-medium ${trend === 'up' ? 'text-alive' : 'text-dead'}`}>
                                {trend === 'up' ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                                {trendValue}
                            </div>
                        )}
                    </div>
                    <div className="space-y-1">
                        <p className="text-2xl font-semibold">
                            <span ref={ref}>{formatNumber(count)}</span>
                            <span className="text-lg text-muted-foreground ml-1">{suffix}</span>
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
    // Default to 0 if value is undefined/null
    const safeValue = value ?? 0;
    const [animatedValue, setAnimatedValue] = useState(0);

    useEffect(() => {
        const timer = setTimeout(() => {
            setAnimatedValue(safeValue);
        }, 500);
        return () => clearTimeout(timer);
    }, [safeValue]);

    const status = safeValue >= 85 ? 'healthy' : safeValue >= 70 ? 'warning' : 'critical';
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
            transition={{ duration: 0.4, delay: 0.24 }}
        >
            <Card className="glass-card">
                <CardHeader className="pb-3">
                    <CardTitle className="text-base font-medium">Overall Survival Rate</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-end justify-between mb-4">
                        <span className="text-4xl font-semibold">{animatedValue.toFixed(1)}%</span>
                        <Badge variant="secondary" className={`${config.color}/10 ${config.textColor} border-0`}>
                            <CheckCircle2 className="w-3 h-3 mr-1" />
                            {config.label}
                        </Badge>
                    </div>

                    <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                        <motion.div
                            className={`absolute inset-y-0 left-0 ${config.color} rounded-full`}
                            initial={{ width: 0 }}
                            animate={{ width: `${animatedValue}%` }}
                            transition={{ duration: 1.2, delay: 0.4, ease: "easeOut" }}
                        />
                        <div className="absolute inset-y-0 left-[85%] w-0.5 bg-forest/40" />
                    </div>

                    <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                        <span>0%</span>
                        <span className="text-forest font-medium">Target: 85%</span>
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
            transition={{ duration: 0.4, delay: 0.32 }}
        >
            <Card className="glass-card h-full">
                <CardHeader className="pb-3">
                    <CardTitle className="text-base font-medium">Monitoring Status</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {[
                        { label: 'Year 1 (2024)', value: yearProgress.year1, status: 'Completed' },
                        { label: 'Year 2 (2025)', value: yearProgress.year2, status: 'In Progress' },
                        { label: 'Year 3 (2026)', value: yearProgress.year3, status: 'In Progress' },
                    ].map((year, index) => (
                        <motion.div
                            key={year.label}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.3, delay: 0.4 + index * 0.08 }}
                            className="space-y-2"
                        >
                            <div className="flex items-center justify-between text-sm">
                                <span className="font-medium">{year.label}</span>
                                <span className="text-muted-foreground">{year.value}% • {year.status}</span>
                            </div>
                            <div className="relative h-1.5 bg-muted rounded-full overflow-hidden">
                                <motion.div
                                    className={`absolute inset-y-0 left-0 rounded-full ${year.value === 100 ? 'bg-alive' : 'bg-forest'}`}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${year.value}%` }}
                                    transition={{ duration: 0.8, delay: 0.5 + index * 0.1, ease: "easeOut" }}
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
function AlertPatchesTable({ patches }: { patches: PatchAlert[] }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.4 }}
        >
            <Card className="glass-card">
                <CardHeader className="pb-4">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-medium flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 text-uncertain" />
                            Patches Requiring Attention
                        </CardTitle>
                        <Button variant="ghost" size="sm" className="text-forest hover:text-forest-light text-sm">
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
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ duration: 0.25, delay: 0.5 + index * 0.04 }}
                                        className={`border-b border-border/50 hover:bg-muted/20 transition-colors ${patch.status === 'critical' ? 'bg-dead/3' : ''}`}
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

// Image Upload Component
function ImageUpload({ onUploadComplete }: { onUploadComplete: () => void }) {
    const [file, setFile] = useState<File | null>(null);
    const [patchName, setPatchName] = useState('');
    const [uploading, setUploading] = useState(false);
    const [status, setStatus] = useState<string>('');
    const [error, setError] = useState<string>('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError('');
        }
    };

    const handleUpload = async () => {
        if (!file) { setError('Please select an image'); return; }
        if (!patchName.trim()) { setError('Please enter patch name'); return; }

        setUploading(true);
        setError('');
        setStatus('Uploading...');

        const result = await api.uploadImage(file, patchName);
        if (result) {
            setStatus('✅ Upload Complete! AI Processing...');
            setTimeout(() => {
                setStatus('✅ Analysis Complete!');
                setUploading(false);
                onUploadComplete();
            }, 3000);
        } else {
            setError('Upload failed');
            setUploading(false);
        }
    };

    return (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.5 }}>
            <Card className="glass-card">
                <CardHeader className="pb-4">
                    <CardTitle className="text-base font-medium flex items-center gap-2">
                        <ArrowUpRight className="w-4 h-4 text-forest" />
                        Upload Drone Image for AI Analysis
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid md:grid-cols-2 gap-6">
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${file ? 'border-forest bg-forest/5' : 'border-border hover:border-forest/50'}`}
                        >
                            <input ref={fileInputRef} type="file" accept=".jpg,.jpeg,.png,.tiff" onChange={handleFileChange} className="hidden" />
                            {file ? (
                                <div className="space-y-2">
                                    <CheckCircle2 className="w-10 h-10 text-forest mx-auto" />
                                    <p className="font-medium text-forest">{file.name}</p>
                                    <p className="text-sm text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <Download className="w-10 h-10 text-muted-foreground mx-auto" />
                                    <p className="font-medium">Drop drone image here</p>
                                    <p className="text-sm text-muted-foreground">JPG, PNG, TIFF supported</p>
                                </div>
                            )}
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="text-sm font-medium mb-2 block">Patch Name</label>
                                <input type="text" placeholder="e.g., Debadihi_VF" value={patchName} onChange={(e) => setPatchName(e.target.value)} className="w-full h-10 px-4 bg-muted/50 rounded-lg border-0 focus:ring-2 focus:ring-forest/50" />
                            </div>
                            {error && <p className="text-sm text-dead">{error}</p>}
                            {status && <p className={`text-sm ${status.includes('✅') ? 'text-alive' : 'text-muted-foreground'}`}>{status}</p>}
                            <Button onClick={handleUpload} disabled={uploading || !file} className="w-full btn-premium gradient-forest text-white border-0">
                                {uploading ? 'Processing...' : 'Analyze with AI'}
                                <TreePine className="w-4 h-4 ml-2" />
                            </Button>
                        </div>
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

            {/* Sidebar - Desktop (Static) */}
            <aside className="hidden lg:flex flex-col fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-30">
                <SidebarContent links={links} />
            </aside>

            {/* Sidebar - Mobile (Animated) */}
            <motion.aside
                initial={{ x: -300 }}
                animate={{ x: isOpen ? 0 : -300 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className="fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-50 lg:hidden"
            >
                <div className="flex flex-col h-full relative">
                    <Button variant="ghost" size="icon" className="absolute top-4 right-4 lg:hidden" onClick={onClose}>
                        <X className="w-5 h-5" />
                    </Button>
                    <SidebarContent links={links} />
                </div>
            </motion.aside>
        </>
    );
}

function SidebarContent({ links }: { links: any[] }) {
    return (
        <div className="flex flex-col h-full">
            {/* Logo */}
            <div className="h-16 flex items-center px-6 border-b border-border">
                <Link href="/" className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg gradient-forest flex items-center justify-center">
                        <Leaf className="w-5 h-5 text-white" />
                    </div>
                    <span className="text-lg font-bold text-gradient">VerdeScan</span>
                </Link>
            </div>

            {/* Navigation */}
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

            {/* User section */}
            <div className="p-4 border-t border-border">
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-muted/50 border border-border/50">
                    <div className="w-10 h-10 rounded-full bg-forest/10 flex items-center justify-center">
                        <span className="text-forest font-semibold text-sm">FO</span>
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">Forest Officer</p>
                        <p className="text-xs text-muted-foreground truncate">Khordha Division</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Main Dashboard Component
export default function DashboardPage() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [selectedYear, setSelectedYear] = useState('2024');
    const [loading, setLoading] = useState(true);
    const [patches, setPatches] = useState<PatchAlert[]>([]);
    const [stats, setStats] = useState<GlobalStats>({
        total_patches: 0,
        total_trees: 0,
        total_alive: 0,
        total_dead: 0,
        total_diseased: 0,
        avg_survival_rate: 0,
        last_updated: ''
    });

    useEffect(() => {
        async function fetchData() {
            setLoading(true);
            try {
                // Fetch stats
                const data = await api.getGlobalStats();
                setStats(data);

                // Fetch patches
                const patchNames = await api.getPatches();
                const patchDetails = await Promise.all(
                    patchNames.slice(0, 5).map(async (name) => {
                        const details = await api.getPatchDetails(name);
                        if (!details) return null;

                        const total = details.summary.total_trees;
                        const validTotal = total > 0 ? total : 1;
                        const survival = (details.summary.alive_trees / validTotal) * 100;

                        let status: 'critical' | 'warning' | 'healthy' = 'healthy';
                        if (survival < 50) status = 'critical';
                        else if (survival < 75) status = 'warning';

                        const date = details.metadata?.timestamp
                            ? new Date(details.metadata.timestamp).toLocaleDateString()
                            : 'Just now';

                        return {
                            id: name.length > 15 ? name.substring(0, 15) + '...' : name,
                            location: `Sector ${name.charAt(0).toUpperCase() + name.slice(1, 3)}`, // Pseudonymize location
                            survival: parseFloat(survival.toFixed(1)),
                            status,
                            lastSurvey: date
                        };
                    })
                );
                setPatches(patchDetails.filter(Boolean) as PatchAlert[]);

            } catch (error) {
                console.error("Failed to fetch dashboard data:", error);
            }
            setLoading(false);
        }
        fetchData();

        // Refresh every 30 seconds
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    const yearProgress = {
        year1: 100,
        year2: 75,
        year3: 25
    };

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
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3 }}
                        className="mb-6"
                    >
                        <h1 className="text-2xl font-semibold mb-1">Dashboard Overview</h1>
                        <p className="text-sm text-muted-foreground">
                            Monitor afforestation health across all patches in real-time
                        </p>
                    </motion.div>

                    {/* KPI Cards Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                        <KPICard
                            icon={MapPin}
                            title="Patches Monitored"
                            value={stats.total_patches}
                            trend="up"
                            trendValue="+4"
                            color="forest"
                            index={0}
                        />
                        <KPICard
                            icon={TreePine}
                            title="Saplings Planted"
                            value={stats.total_trees}
                            color="earth"
                            index={1}
                        />
                        <KPICard
                            icon={CheckCircle2}
                            title="Saplings Alive"
                            value={stats.total_alive}
                            color="alive"
                            index={2}
                        />
                        <KPICard
                            icon={XCircle}
                            title="Saplings Dead"
                            value={stats.total_dead}
                            color="dead"
                            index={3}
                        />
                    </div>

                    {/* Survival Rate and Year Progress */}
                    <div className="grid lg:grid-cols-2 gap-4 mb-8">
                        <SurvivalGauge value={stats.avg_survival_rate} />
                        <YearProgress yearProgress={yearProgress} />
                    </div>

                    {/* Alert Patches Table */}
                    <AlertPatchesTable patches={patches} />

                    {/* Image Upload Section */}
                    <div className="mt-8">
                        <ImageUpload onUploadComplete={() => {
                            // Refresh stats after upload
                            api.getGlobalStats().then(setStats);
                        }} />
                    </div>

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
