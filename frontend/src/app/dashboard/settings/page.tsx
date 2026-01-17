'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
    Settings as SettingsIcon,
    User,
    Bell,
    Shield,
    Database,
    Palette,
    Globe,
    Save,
    Menu,
    Leaf,
    Home,
    Map,
    Layers,
    BarChart3,
    FileText,
    X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Link from 'next/link';
import { AnimatePresence } from 'framer-motion';

// Sidebar Component
function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const links = [
        { icon: Home, label: 'Dashboard', href: '/dashboard' },
        { icon: Map, label: 'Patch Explorer', href: '/dashboard/explorer' },
        { icon: Layers, label: 'Temporal View', href: '/dashboard/temporal' },
        { icon: BarChart3, label: 'Analytics', href: '/dashboard/analytics' },
        { icon: FileText, label: 'Reports', href: '/dashboard/reports' },
        { icon: SettingsIcon, label: 'Settings', href: '/dashboard/settings', active: true },
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

export default function SettingsPage() {
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
                                <h1 className="font-semibold">Settings</h1>
                                <p className="text-xs text-muted-foreground">Manage your preferences</p>
                            </div>
                        </div>

                        <Button size="sm" className="bg-forest text-white hover:bg-forest-light">
                            <Save className="w-4 h-4 mr-2" />
                            Save Changes
                        </Button>
                    </div>
                </header>

                {/* Main Content */}
                <main className="p-4 lg:p-8">
                    <Tabs defaultValue="profile" className="space-y-6">
                        <TabsList className="bg-muted">
                            <TabsTrigger value="profile">Profile</TabsTrigger>
                            <TabsTrigger value="notifications">Notifications</TabsTrigger>
                            <TabsTrigger value="security">Security</TabsTrigger>
                            <TabsTrigger value="data">Data</TabsTrigger>
                        </TabsList>

                        <TabsContent value="profile" className="space-y-4">
                            <Card className="glass-card">
                                <CardHeader>
                                    <CardTitle className="text-base font-medium flex items-center gap-2">
                                        <User className="w-4 h-4" />
                                        Profile Information
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div>
                                        <label className="text-sm font-medium mb-2 block">Full Name</label>
                                        <input
                                            type="text"
                                            defaultValue="Forest Officer"
                                            className="w-full h-10 px-4 bg-muted rounded-lg border-0 focus:ring-2 focus:ring-forest/50 text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium mb-2 block">Division</label>
                                        <input
                                            type="text"
                                            defaultValue="Khordha Division"
                                            className="w-full h-10 px-4 bg-muted rounded-lg border-0 focus:ring-2 focus:ring-forest/50 text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium mb-2 block">Email</label>
                                        <input
                                            type="email"
                                            defaultValue="officer@forest.gov.in"
                                            className="w-full h-10 px-4 bg-muted rounded-lg border-0 focus:ring-2 focus:ring-forest/50 text-sm"
                                        />
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="notifications" className="space-y-4">
                            <Card className="glass-card">
                                <CardHeader>
                                    <CardTitle className="text-base font-medium flex items-center gap-2">
                                        <Bell className="w-4 h-4" />
                                        Notification Preferences
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    {[
                                        { id: 'critical', label: 'Critical Patches', desc: 'Patches below 70% survival' },
                                        { id: 'weekly', label: 'Weekly Reports', desc: 'Summary every Monday' },
                                        { id: 'survey', label: 'Survey Reminders', desc: 'Upcoming survey notifications' },
                                    ].map((item) => (
                                        <label key={item.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg cursor-pointer hover:bg-muted">
                                            <div>
                                                <p className="text-sm font-medium">{item.label}</p>
                                                <p className="text-xs text-muted-foreground">{item.desc}</p>
                                            </div>
                                            <input type="checkbox" defaultChecked className="w-4 h-4 rounded text-forest focus:ring-forest" />
                                        </label>
                                    ))}
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="security" className="space-y-4">
                            <Card className="glass-card">
                                <CardHeader>
                                    <CardTitle className="text-base font-medium flex items-center gap-2">
                                        <Shield className="w-4 h-4" />
                                        Security Settings
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div>
                                        <label className="text-sm font-medium mb-2 block">Current Password</label>
                                        <input
                                            type="password"
                                            className="w-full h-10 px-4 bg-muted rounded-lg border-0 focus:ring-2 focus:ring-forest/50 text-sm"
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium mb-2 block">New Password</label>
                                        <input
                                            type="password"
                                            className="w-full h-10 px-4 bg-muted rounded-lg border-0 focus:ring-2 focus:ring-forest/50 text-sm"
                                        />
                                    </div>
                                    <Button variant="outline" size="sm">Update Password</Button>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="data" className="space-y-4">
                            <Card className="glass-card">
                                <CardHeader>
                                    <CardTitle className="text-base font-medium flex items-center gap-2">
                                        <Database className="w-4 h-4" />
                                        Data Management
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                                        <div>
                                            <p className="text-sm font-medium">Export All Data</p>
                                            <p className="text-xs text-muted-foreground">Download complete dataset</p>
                                        </div>
                                        <Button variant="outline" size="sm">Export</Button>
                                    </div>
                                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                                        <div>
                                            <p className="text-sm font-medium">Clear Cache</p>
                                            <p className="text-xs text-muted-foreground">Free up storage space</p>
                                        </div>
                                        <Button variant="outline" size="sm">Clear</Button>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </main>
            </div>
        </div>
    );
}
