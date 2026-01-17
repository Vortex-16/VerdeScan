"use client";

import { useRef, useEffect } from "react";
import { motion, useInView } from "framer-motion";

export default function ScrollVideo({ src, className = "" }: { src: string; className?: string }) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const isInView = useInView(videoRef, { amount: 0.5 });

    useEffect(() => {
        if (isInView) {
            videoRef.current?.play();
        } else {
            videoRef.current?.pause();
        }
    }, [isInView]);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className={`relative overflow-hidden rounded-2xl ${className}`}
        >
            <video
                ref={videoRef}
                src={src}
                muted
                loop
                playsInline
                className="w-full h-full object-cover"
            />

            {/* Overlay gradient */}
            <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-transparent pointer-events-none" />

            {/* Play indicator */}
            <div className={`absolute bottom-6 right-6 px-3 py-1 bg-black/50 backdrop-blur-md rounded-full text-xs font-mono text-white/80 transition-opacity duration-300 ${isInView ? 'opacity-0' : 'opacity-100'}`}>
                SCROLL TO PLAY
            </div>
        </motion.div>
    );
}
