'use client';

import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Home, Map, Layers, BarChart3, FileText, Settings, Leaf, X
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface NavLink {
    icon: React.ElementType;
    label: string;
    href: string;
    active?: boolean;
}

interface DashboardSidebarProps {
    /** Which page is currently active — matches the `label` of a nav link */
    activePage: 'Dashboard' | 'Patch Explorer' | 'Temporal View' | 'Analytics' | 'Reports' | 'Settings';
    /** Whether the mobile drawer is open */
    isOpen: boolean;
    onClose: () => void;
}

const NAV_LINKS: NavLink[] = [
    { icon: Home,     label: 'Dashboard',     href: '/dashboard' },
    { icon: Map,      label: 'Patch Explorer', href: '/dashboard/explorer' },
    { icon: Layers,   label: 'Temporal View',  href: '/dashboard/temporal' },
    { icon: BarChart3,label: 'Analytics',      href: '/dashboard/analytics' },
    { icon: FileText, label: 'Reports',        href: '/dashboard/reports' },
    { icon: Settings, label: 'Settings',       href: '/dashboard/settings' },
];

function SidebarContent({ links }: { links: NavLink[] }) {
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
                        className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                            link.active
                                ? 'bg-forest text-white shadow-lg shadow-forest/25'
                                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                        }`}
                    >
                        <link.icon
                            className={`w-5 h-5 ${link.active ? '' : 'group-hover:scale-110'} transition-transform`}
                        />
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

/**
 * Shared sidebar used across all dashboard pages.
 * Pass `activePage` to highlight the current route.
 */
export default function DashboardSidebar({ activePage, isOpen, onClose }: DashboardSidebarProps) {
    const links = NAV_LINKS.map((l) => ({ ...l, active: l.label === activePage }));

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

            {/* Desktop — static */}
            <aside className="hidden lg:flex flex-col fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-30">
                <SidebarContent links={links} />
            </aside>

            {/* Mobile — animated drawer */}
            <motion.aside
                initial={{ x: -300 }}
                animate={{ x: isOpen ? 0 : -300 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                className="fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-50 lg:hidden"
            >
                <div className="flex flex-col h-full relative">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="absolute top-4 right-4"
                        onClick={onClose}
                    >
                        <X className="w-5 h-5" />
                    </Button>
                    <SidebarContent links={links} />
                </div>
            </motion.aside>
        </>
    );
}
