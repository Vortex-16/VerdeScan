'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
    FileText,
    Download,
    Calendar,
    Filter,
    Menu,
    Leaf,
    Home,
    Map,
    Layers,
    BarChart3,
    Settings,
    X,
    Clock,
    CheckCircle2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { AnimatePresence } from 'framer-motion';

// Mock data
const recentReports = [
    { id: 1, name: 'Q4 2024 State Summary', date: '2024-12-31', size: '2.4 MB', format: 'PDF', status: 'completed' },
    { id: 2, name: 'Khordha District Report', date: '2024-12-15', size: '1.8 MB', format: 'PDF', status: 'completed' },
    { id: 3, name: 'Critical Patches Analysis', date: '2024-12-01', size: '3.1 MB', format: 'Excel', status: 'completed' },
    { id: 4, name: 'Annual Summary 2024', date: '2024-11-30', size: '5.2 MB', format: 'PDF', status: 'completed' },
];

// Sidebar Component
function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const links = [
        { icon: Home, label: 'Dashboard', href: '/dashboard' },
        { icon: Map, label: 'Patch Explorer', href: '/dashboard/explorer' },
        { icon: Layers, label: 'Temporal View', href: '/dashboard/temporal' },
        { icon: BarChart3, label: 'Analytics', href: '/dashboard/analytics' },
        { icon: FileText, label: 'Reports', href: '/dashboard/reports', active: true },
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
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
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

export default function ReportsPage() {
    const [sidebarOpen, setSidebarOpen] = useState(false);

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
                                <h1 className="font-semibold">Reports</h1>
                                <p className="text-xs text-muted-foreground">Generate and download reports</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm">
                                <Filter className="w-4 h-4 mr-2" />
                                Filter
                            </Button>
                            <Link href="/dashboard/analytics">
                                <Button size="sm" className="bg-forest text-white hover:bg-forest-light">
                                    <FileText className="w-4 h-4 mr-2" />
                                    New Report
                                </Button>
                            </Link>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="p-4 lg:p-8">
                    {/* Recent Reports */}
                    <Card className="glass-card">
                        <CardHeader>
                            <CardTitle className="text-base font-medium flex items-center gap-2">
                                <Clock className="w-4 h-4" />
                                Recent Reports
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                {recentReports.map((report, index) => (
                                    <motion.div
                                        key={report.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="flex items-center justify-between p-3 bg-muted/30 rounded-lg hover:bg-muted/50 transition-colors group"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-lg bg-forest/10 flex items-center justify-center">
                                                <FileText className="w-5 h-5 text-forest" />
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium">{report.name}</p>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <Calendar className="w-3 h-3" />
                                                    {report.date}
                                                    <span>•</span>
                                                    <span>{report.size}</span>
                                                    <Badge variant="secondary" className="text-xs">
                                                        {report.format}
                                                    </Badge>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Badge variant="secondary" className="bg-alive/10 text-alive border-0 text-xs">
                                                <CheckCircle2 className="w-3 h-3 mr-1" />
                                                {report.status}
                                            </Badge>
                                            <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Download className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Quick Actions */}
                    <div className="grid md:grid-cols-3 gap-4 mt-6">
                        <Card className="glass-card">
                            <CardContent className="p-5">
                                <div className="w-10 h-10 rounded-lg bg-forest/10 flex items-center justify-center mb-3">
                                    <FileText className="w-5 h-5 text-forest" />
                                </div>
                                <h3 className="font-medium mb-1">State Summary</h3>
                                <p className="text-xs text-muted-foreground mb-3">Complete state-level overview</p>
                                <Button variant="outline" size="sm" className="w-full">Generate</Button>
                            </CardContent>
                        </Card>

                        <Card className="glass-card">
                            <CardContent className="p-5">
                                <div className="w-10 h-10 rounded-lg bg-alive/10 flex items-center justify-center mb-3">
                                    <Map className="w-5 h-5 text-alive" />
                                </div>
                                <h3 className="font-medium mb-1">District Report</h3>
                                <p className="text-xs text-muted-foreground mb-3">Detailed district analysis</p>
                                <Button variant="outline" size="sm" className="w-full">Generate</Button>
                            </CardContent>
                        </Card>

                        <Card className="glass-card">
                            <CardContent className="p-5">
                                <div className="w-10 h-10 rounded-lg bg-earth/10 flex items-center justify-center mb-3">
                                    <BarChart3 className="w-5 h-5 text-earth" />
                                </div>
                                <h3 className="font-medium mb-1">Custom Report</h3>
                                <p className="text-xs text-muted-foreground mb-3">Build your own report</p>
                                <Link href="/dashboard/analytics">
                                    <Button variant="outline" size="sm" className="w-full">Create</Button>
                                </Link>
                            </CardContent>
                        </Card>
                    </div>
                </main>
            </div>
        </div>
    );
}
