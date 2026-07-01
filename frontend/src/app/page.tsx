'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion';
import {
  TreePine,
  Satellite,
  BarChart3,
  MapPin,
  Leaf,
  Zap,
  Shield,
  ArrowRight,
  ChevronDown,
  Play,
  CheckCircle2,
  TrendingUp,
  Users,
  Globe,
  Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import Link from 'next/link';
import MagneticButton from '@/components/ui/magnetic-button';

// Scroll state hook
function useScrollState(threshold: number = 50) {
  const [isScrolled, setIsScrolled] = useState(false);
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > threshold);
    };
    window.addEventListener('scroll', handleScroll);
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, [threshold]);
  return isScrolled;
}

// Counter animation hook
function useCounter(target: number, duration: number = 2000, startOnView: boolean = true) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const hasAnimated = useRef(false);

  useEffect(() => {
    if (!startOnView || hasAnimated.current) return;

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
  }, [target, duration, startOnView]);

  return { count, ref };
}

// Animated text reveal component
function AnimatedText({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  return (
    <motion.span
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {text}
    </motion.span>
  );
}

// Dynamic Drone Telemetry Component
function DroneTelemetry() {
  const [telemetry, setTelemetry] = useState({
    altitude: 120,
    speed: 12,
    battery: 84,
    iso: 400,
    shutter: 200,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry({
        altitude: 115 + Math.random() * 10, // 115-125m
        speed: 10 + Math.random() * 4, // 10-14 m/s
        battery: 82 + Math.random() * 4, // 82-86%
        iso: 200 + Math.floor(Math.random() * 600), // 200-800
        shutter: 125 + Math.floor(Math.random() * 275), // 1/125 - 1/400
      });
    }, 800 + Math.random() * 400); // Random interval between 800-1200ms

    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div className="absolute top-12 left-28 font-mono text-xs text-white/60 transition-all duration-300">
        <div>ALT: {telemetry.altitude.toFixed(0)}m</div>
        <div>SPD: {telemetry.speed.toFixed(1)}m/s</div>
        <div>BAT: {telemetry.battery.toFixed(0)}%</div>
      </div>
      <div className="absolute bottom-12 right-28 font-mono text-xs text-white/60 text-right transition-all duration-300">
        <div className="flex items-center gap-2 justify-end">
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          RECORDING
        </div>
        <div>ISO: {telemetry.iso}</div>
        <div>SHUTTER: 1/{telemetry.shutter}</div>
      </div>
    </>
  );
}

// Feature Card Component
function FeatureCard({
  icon: Icon,
  title,
  description,
  index
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.6, delay: index * 0.1, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="glass-card group hover:border-forest/30 transition-all duration-500 h-full cursor-pointer">
        <CardContent className="p-6">
          <div className="w-12 h-12 rounded-xl bg-forest/10 flex items-center justify-center mb-4 group-hover:bg-forest group-hover:scale-110 transition-all duration-300">
            <Icon className="w-6 h-6 text-forest group-hover:text-white transition-colors duration-300" />
          </div>
          <h3 className="text-lg font-semibold mb-2 group-hover:text-forest transition-colors duration-300">{title}</h3>
          <p className="text-muted-foreground text-sm leading-relaxed">{description}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// Stat Card Component
function StatCard({ value, suffix, label, index }: { value: number; suffix: string; label: string; index: number }) {
  const { count, ref } = useCounter(value, 2000);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="text-center"
    >
      <div className="text-4xl md:text-5xl font-bold text-gradient mb-2">
        <span ref={ref} className="counter-animate">{count.toLocaleString()}</span>
        <span className="text-forest-light">{suffix}</span>
      </div>
      <p className="text-muted-foreground">{label}</p>
    </motion.div>
  );
}

// Floating Elements
// Parallax Background
function ParallaxBackground() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });

  const y = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0.3]);

  return (
    <div ref={ref} className="absolute inset-0 z-0 overflow-hidden h-[120vh]">
      <motion.div style={{ y, opacity }} className="absolute inset-0">
        {/* Video Background */}
        <video
          autoPlay
          muted
          loop
          playsInline
          className="w-full h-full object-cover"
          src="/videos/treeAnime.mp4"
        />
      </motion.div>
    </div>
  );
}

// Main Page Component
export default function LandingPage() {
  const isScrolled = useScrollState();
  const heroRef = useRef<HTMLDivElement>(null);
  const featuresRef = useRef<HTMLDivElement>(null);
  const cursorRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll();
  const heroOpacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 0.2], [1, 0.95]);

  // Cursor glow effect

  const features = [
    {
      icon: Satellite,
      title: 'Drone-Powered Analysis',
      description: 'High-resolution orthomosaic imagery captured by professional drones for accurate monitoring.',
    },
    {
      icon: Zap,
      title: 'AI-Driven Detection',
      description: 'Machine learning algorithms detect individual saplings and assess survival with 95%+ accuracy.',
    },
    {
      icon: MapPin,
      title: 'Precise Geolocation',
      description: 'GPS coordinates for every sapling, enabling field teams to navigate to exact locations.',
    },
    {
      icon: BarChart3,
      title: 'Real-time Analytics',
      description: 'Interactive dashboards with survival trends, district comparisons, and automated reports.',
    },
    {
      icon: Shield,
      title: 'Audit-Ready Reports',
      description: 'Comprehensive documentation for government compliance and policy review.',
    },
    {
      icon: Globe,
      title: 'State-wide Scale',
      description: 'Monitor millions of saplings across thousands of patches efficiently.',
    },
  ];

  const stats = [
    { value: 5, suffix: ' Cr+', label: 'Trees Planted Annually' },
    { value: 247, suffix: '+', label: 'Patches Monitored' },
    { value: 95, suffix: '%', label: 'Detection Accuracy' },
    { value: 30, suffix: 's', label: 'Time to Insights' },
  ];

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Cursor glow */}
      <div ref={cursorRef} className="cursor-glow hidden md:block" />



      {/* Particle container */}
      <div className="particle-container fixed inset-0 pointer-events-none overflow-hidden z-0" />

      {/* Navigation */}
      <nav
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${isScrolled ? 'glass py-3' : 'bg-transparent py-5'}`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl gradient-forest flex items-center justify-center">
                <Leaf className="w-6 h-6 text-white" />
              </div>
              <span className={`text-xl font-bold transition-colors ${isScrolled ? 'text-gradient' : 'text-white'}`}>VerdeScan</span>
            </div>

            <div className="hidden md:flex items-center gap-8">
              {['Features', 'How it Works', 'Impact'].map((item) => (
                <Link
                  key={item}
                  href={`#${item.toLowerCase().replace(/\s+/g, '-')}`}
                  className={`transition-colors line-decoration ${isScrolled ? 'text-muted-foreground hover:text-forest' : 'text-white/80 hover:text-white'}`}
                >
                  {item}
                </Link>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <Link href="/dashboard">
                <Button variant="ghost" className={`hidden sm:flex ${isScrolled ? '' : 'text-white hover:bg-white/10 hover:text-white'}`}>
                  Dashboard
                </Button>
              </Link>
              <Link href="/dashboard">
                <MagneticButton>
                  <Button className="btn-premium gradient-forest text-white border-0">
                    Get Started
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </MagneticButton>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <motion.section
        ref={heroRef}
        style={{ opacity: heroOpacity, scale: heroScale }}
        className="relative min-h-screen flex items-center justify-center pt-16 overflow-hidden"
      >
        <ParallaxBackground />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 relative z-10">
          <div className="text-center">
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="mb-6"
            >
              <Badge variant="secondary" className="px-4 py-1.5 text-sm font-bold backdrop-blur-md bg-white/20 text-white border border-white/30 hover:bg-white/30">
                <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                AI-Powered Afforestation Monitoring
              </Badge>
            </motion.div>

            {/* Main Title */}
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-6 perspective-1000 text-white drop-shadow-2xl">
              <span className="hero-title-word inline-block">Track</span>{' '}
              <span className="hero-title-word inline-block text-gradient-orange">Every</span>{' '}
              <span className="hero-title-word inline-block">Sapling,</span>
              <br />
              <span className="hero-title-word inline-block">Protect</span>{' '}
              <span className="hero-title-word inline-block text-gradient-orange">Every</span>{' '}
              <span className="hero-title-word inline-block">Forest</span>
            </h1>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="text-xl md:text-2xl text-white/90 max-w-3xl mx-auto mb-10 drop-shadow-lg"
            >
              AI-powered drone imagery analysis for monitoring{' '}
              <span className="text-yellow-400 font-medium drop-shadow-lg">5 Crore+ saplings</span> annually.
              Replace manual surveys with precision technology.
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 1 }}
              className="flex flex-col sm:flex-row gap-4 justify-center items-center"
            >
              <Link href="/dashboard">
                <Button size="lg" className="btn-premium gradient-forest text-white border-0 h-14 px-8 text-lg">
                  Launch Dashboard
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
              <Button size="lg" variant="outline" className="h-14 px-8 text-lg group">
                <Play className="w-5 h-5 mr-2 group-hover:scale-110 transition-transform" />
                Watch Demo
              </Button>
            </motion.div>

            {/* Trust badges */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 1.2 }}
              className="mt-12 flex flex-wrap justify-center gap-6 text-sm"
            >
              <div className="flex items-center gap-2 px-4 py-2 rounded-full backdrop-blur-md bg-white/20 border border-white/30">
                <CheckCircle2 className="w-4 h-4 text-alive" />
                <span className="text-emerald-900 font-medium">Odisha Forest Department</span>
              </div>
              <div className="flex items-center gap-2 px-4 py-2 rounded-full backdrop-blur-md bg-white/20 border border-white/30">
                <CheckCircle2 className="w-4 h-4 text-alive" />
                <span className="text-emerald-900 font-medium">Government Approved</span>
              </div>
              <div className="flex items-center gap-2 px-4 py-2 rounded-full backdrop-blur-md bg-white/20 border border-white/30">
                <CheckCircle2 className="w-4 h-4 text-alive" />
                <span className="text-emerald-900 font-medium">ISO Certified</span>
              </div>
            </motion.div>
          </div>

          {/* Scroll indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5, duration: 0.6 }}
            className="absolute bottom-10 left-1/2 -translate-x-1/2"
          >
            <motion.div
              animate={{ y: [0, 10, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="flex flex-col items-center gap-2 text-muted-foreground"
            >
              <span className="text-sm">Scroll to explore</span>
              <ChevronDown className="w-5 h-5" />
            </motion.div>
          </motion.div>
        </div>

        {/* Drone HUD Overlay */}
        <div className="absolute inset-0 pointer-events-none z-0">
          {/* Central reticle */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 1, duration: 1 }}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] border border-white/10 rounded-full opacity-20"
          />
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[580px] h-[580px] border-t border-b border-white/20 rounded-full opacity-30"
          />

          {/* Corner brackets */}
          <div className="absolute top-10 left-10 w-16 h-16 border-t-2 border-l-2 border-white/20" />
          <div className="absolute top-10 right-10 w-16 h-16 border-t-2 border-r-2 border-white/20" />
          <div className="absolute bottom-10 left-10 w-16 h-16 border-b-2 border-l-2 border-white/20" />
          <div className="absolute bottom-10 right-10 w-16 h-16 border-b-2 border-r-2 border-white/20" />

          {/* Data readouts - Dynamic Telemetry */}
          <DroneTelemetry />
        </div>
      </motion.section>

      {/* Stats Section */}
      <section className="py-20 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="glass-card rounded-2xl p-8 md:p-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {stats.map((stat, index) => (
                <StatCard key={index} {...stat} index={index} />
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" ref={featuresRef} className="py-20 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <Badge variant="secondary" className="mb-4 bg-forest/10 text-forest border-forest/20">
              Features
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Everything you need for
              <span className="text-gradient"> forest monitoring</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              From drone capture to actionable insights, our platform handles the complete monitoring workflow.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <div key={index} className="feature-card">
                <FeatureCard {...feature} index={index} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 relative z-10 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <Badge variant="secondary" className="mb-4 bg-forest/10 text-forest border-forest/20">
              Process
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              From drone to
              <span className="text-gradient"> decision</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              A streamlined workflow that turns aerial imagery into actionable survival data.
            </p>
          </motion.div>

          <div className="relative">
            {/* Connection line */}
            <div className="process-line hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-forest/30 to-transparent -translate-y-1/2" />

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
              {[
                { step: '01', title: 'Drone Survey', description: 'Field teams capture high-resolution orthomosaic imagery using professional drones.', icon: Satellite },
                { step: '02', title: 'AI Processing', description: 'Machine learning algorithms detect and classify each sapling automatically.', icon: Zap },
                { step: '03', title: 'Dashboard Analysis', description: 'Interactive maps and charts reveal survival patterns and problem areas.', icon: BarChart3 },
                { step: '04', title: 'Field Action', description: 'Officers receive precise coordinates to verify and take corrective action.', icon: MapPin },
              ].map((item, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.15 }}
                  className="relative"
                >
                  <Card className="glass-card h-full group hover:border-forest/30 transition-all duration-300">
                    <CardContent className="p-6 text-center">
                      <div className="w-16 h-16 rounded-full gradient-forest mx-auto mb-4 flex items-center justify-center relative">
                        <item.icon className="w-8 h-8 text-white" />
                        <span className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-background border-2 border-forest flex items-center justify-center text-sm font-bold text-forest">
                          {item.step}
                        </span>
                      </div>
                      <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                      <p className="text-muted-foreground text-sm">{item.description}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Impact Section */}
      <section id="impact" className="py-20 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="glass-card rounded-2xl p-8 md:p-12 relative overflow-hidden">
            <div className="absolute inset-0 gradient-radial-glow opacity-50" />

            <div className="relative z-10 grid lg:grid-cols-2 gap-12 items-center">
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
              >
                <Badge variant="secondary" className="mb-4 bg-forest/10 text-forest border-forest/20">
                  Impact
                </Badge>
                <h2 className="text-4xl md:text-5xl font-bold mb-6">
                  Making afforestation
                  <span className="text-gradient"> accountable</span>
                </h2>
                <p className="text-lg text-muted-foreground mb-8">
                  Traditional manual surveys cover only 5% of forest patches. VerdeScan enables 100% coverage,
                  ensuring every planted sapling is tracked and every forest officer has the data they need.
                </p>

                <div className="space-y-4">
                  {[
                    'Reduce manual survey costs by 80%',
                    'Identify dead saplings within days, not months',
                    'Enable data-driven replanting decisions',
                    'Build transparent audit trails for policymakers',
                  ].map((item, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.4, delay: index * 0.1 }}
                      className="flex items-center gap-3"
                    >
                      <div className="w-6 h-6 rounded-full bg-alive/20 flex items-center justify-center flex-shrink-0">
                        <CheckCircle2 className="w-4 h-4 text-alive" />
                      </div>
                      <span>{item}</span>
                    </motion.div>
                  ))}
                </div>
              </motion.div>

              <div className="relative h-[400px] rounded-2xl overflow-hidden shadow-2xl border border-white/10">
                <img
                  src="/images/hero-bg.png"
                  alt="Drone Analysis"
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-forest/10" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 relative z-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-6">
              Ready to transform
              <span className="text-gradient"> forest monitoring?</span>
            </h2>
            <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
              Join the digital revolution in afforestation tracking. Get started with VerdeScan today.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/dashboard">
                <Button size="lg" className="btn-premium gradient-forest text-white border-0 h-14 px-10 text-lg">
                  Launch Dashboard
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
              <Button size="lg" variant="outline" className="h-14 px-10 text-lg">
                <Users className="w-5 h-5 mr-2" />
                Contact Team
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg gradient-forest flex items-center justify-center">
                <Leaf className="w-4 h-4 text-white" />
              </div>
              <span className="font-semibold">VerdeScan</span>
            </div>

            <p className="text-muted-foreground text-sm text-center">
              AI-powered afforestation monitoring for the Odisha Forest Department
            </p>

            <p className="text-muted-foreground text-sm">
              © 2026 VerdeScan. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
