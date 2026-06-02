import { useEffect, useRef, useState } from 'react';

/**
 * Animates a numeric counter from 0 to `target` when the element scrolls into view.
 * Handles elements that are already visible on mount — IntersectionObserver only fires
 * on intersection transitions, so we check visibility manually after attaching.
 */
export function useCounter(target: number, duration: number = 2000) {
    const [count, setCount] = useState(0);
    const ref = useRef<HTMLSpanElement>(null);
    const hasAnimated = useRef(false);
    const prevTarget = useRef<number>(-1);

    useEffect(() => {
        if (target !== prevTarget.current) {
            hasAnimated.current = false;
            prevTarget.current = target;
        }

        const runAnimation = () => {
            if (hasAnimated.current) return;
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
                    setCount(target);
                }
            };
            animate();
        };

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) runAnimation();
            },
            { threshold: 0.5 }
        );

        if (ref.current) {
            observer.observe(ref.current);
            // IntersectionObserver only fires on transitions, not for elements that are
            // already intersecting when observe() is called. Check synchronously so
            // above-the-fold KPI cards animate when data arrives after mount.
            const rect = ref.current.getBoundingClientRect();
            const viewH = window.innerHeight || document.documentElement.clientHeight;
            const centerY = (rect.top + rect.bottom) / 2;
            if (centerY >= 0 && centerY <= viewH) {
                runAnimation();
            }
        }

        return () => observer.disconnect();
    }, [target, duration]);

    return { count, ref };
}
