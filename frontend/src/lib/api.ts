// Local development: Use localhost. For production, set NEXT_PUBLIC_API_URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';

export interface GlobalStats {
    total_patches: number;
    total_trees: number;
    total_alive: number;
    total_dead: number;
    total_diseased: number;
    avg_survival_rate: number;
    last_updated: string;
    message?: string;
}

/**
 * A single detected tree, exactly as serialised by the backend.
 * The backend stores status as uppercase enum values: "ALIVE", "DEAD", "DISEASED".
 */
export interface TreeDetail {
    tree_id: string | number;
    /** Uppercase: "ALIVE" | "DEAD" | "DISEASED" */
    status: 'ALIVE' | 'DEAD' | 'DISEASED' | string;
    detection_confidence: number;
    classification_confidence: number;
    bbox: { x: number; y: number; width: number; height: number };
    center?: [number, number];
    gps?: { lat: number; lng: number; altitude?: number };
    proof_image?: string;
}

export interface PatchSummary {
    total_trees: number;
    alive_trees: number;
    dead_trees: number;
    diseased_trees: number;
    survival_rate?: number;
}

export interface PatchMetadata {
    patch_id?: string;
    filename?: string;
    file_size?: number;
    dimensions?: [number, number];
    format?: string;
    processing_time?: number;
    timestamp?: string;
}

export interface PatchData {
    /** Injected by the backend / API layer */
    patch_id: string;
    summary: PatchSummary;
    /** 'trees' is an alias for 'details' in the JSON — backend sends both */
    trees: TreeDetail[];
    /** Raw 'details' array, same data as trees */
    details?: TreeDetail[];
    metadata?: PatchMetadata;
    processing_time?: number;
}

export interface SiteMarker {
    lat: number;
    lon: number;
    conf: number;
    /** ExG vegetation fraction in the central disc (sapling presence) */
    green_center?: number;
    /** Weeding-ring contrast (cleared centre vs vegetated surround) */
    ring_contrast?: number;
}

export interface SiteResult {
    site: string;
    status: 'complete' | 'running' | 'not_started' | string;
    total_detected?: number;
    in_field?: number;
    alive?: number;
    dead?: number;
    /** Pits that could not be judged because they fell in a nodata hole */
    no_data?: number;
    /** Pits outside the OP3 footprint */
    out_of_bounds?: number;
    survival_pct?: number;
    casualties?: SiteMarker[];
    alive_locations?: SiteMarker[];
    message?: string;
}

/** One ground-truth dead location scored against the pipeline's casualties. */
export interface EvalPoint {
    lat: number;
    lon: number;
    /** true if a predicted casualty lies within tolerance */
    matched: boolean;
    /** metres to the matched casualty (or to the nearest detection if missed) */
    distance: number;
    /** pipeline status at the nearest detection: 'dead' = correct, 'alive' = a real miss */
    nearest_status?: string | null;
}

export interface EvalResult {
    site: string;
    tol: number;
    total_truth: number;
    matched: number;
    /** recall as a percentage (0-100) */
    recall: number;
    mean_dist?: number | null;
    median_dist?: number | null;
    max_dist?: number | null;
    points: EvalPoint[];
}

export interface SurveyPoint {
    task_id: string;
    patch_id: string;
    lat: number;
    lon: number;
    uploaded_at: string;
    total_trees?: number;
    alive_trees?: number;
    dead_trees?: number;
    survival_pct?: number;
}

export interface SiteSurveyResponse {
    site: string;
    surveys: SurveyPoint[];
}

export interface TaskStatusResponse {
    task_id: string;
    status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled' | string;
    progress: number;
    created_at?: string;
    updated_at?: string;
    estimated_time_remaining?: number;
    error_message?: string;
    result?: {
        patch_id: string;
        processing_time: number;
        summary: PatchSummary;
    };
}

export const api = {
    async getGlobalStats(): Promise<GlobalStats> {
        try {
            const res = await fetch(`${API_BASE_URL}/stats`, { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to fetch stats');
            return await res.json();
        } catch (error) {
            console.error('API Error [getGlobalStats]:', error);
            return {
                total_patches: 0,
                total_trees: 0,
                total_alive: 0,
                total_dead: 0,
                total_diseased: 0,
                avg_survival_rate: 0,
                last_updated: new Date().toISOString(),
            };
        }
    },

    async getPatches(): Promise<string[]> {
        try {
            const res = await fetch(`${API_BASE_URL}/patches`, { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to fetch patches');
            return await res.json();
        } catch (error) {
            console.error('API Error [getPatches]:', error);
            return [];
        }
    },

    async getPatchDetails(patchId: string): Promise<PatchData | null> {
        try {
            const res = await fetch(`${API_BASE_URL}/patch/${encodeURIComponent(patchId)}`, { cache: 'no-store' });
            if (!res.ok) throw new Error(`Failed to fetch patch '${patchId}'`);
            const data = await res.json();
            // Ensure trees field exists (alias for details)
            if (!data.trees && data.details) data.trees = data.details;
            return data as PatchData;
        } catch (error) {
            console.error('API Error [getPatchDetails]:', error);
            return null;
        }
    },

    async getAllPatchDetails(): Promise<PatchData[]> {
        try {
            const res = await fetch(`${API_BASE_URL}/patches/all`, { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to fetch all patch details');
            const list: PatchData[] = await res.json();
            // Normalise each entry
            return list.map((item) => {
                if (!item.trees && item.details) item.trees = item.details;
                return item;
            });
        } catch (error) {
            console.error('API Error [getAllPatchDetails]:', error);
            return [];
        }
    },

    async uploadImage(
        file: File,
        patchName: string,
        site?: string,
    ): Promise<{ task_id: string; status: string; camera_gps?: { lat: number; lon: number } | null } | null> {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('patch_name', patchName);
            if (site) formData.append('site', site);

            const res = await fetch(`${API_BASE_URL}/upload-image`, {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
                throw new Error(err.detail || 'Upload failed');
            }
            return await res.json();
        } catch (error) {
            console.error('Upload Error:', error);
            return null;
        }
    },

    async getTaskStatus(taskId: string): Promise<TaskStatusResponse | null> {
        try {
            const res = await fetch(`${API_BASE_URL}/task-status/${taskId}`, { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to get task status');
            return await res.json();
        } catch (error) {
            console.error('API Error [getTaskStatus]:', error);
            return null;
        }
    },

    /** Returns the full URL to an uploaded image served from /api/uploads/<filename> */
    getImageUrl(filename: string): string {
        return `${API_BASE_URL}/uploads/${filename}`;
    },

    async analyzeSite(site: 'benkmura' | 'debadihi'): Promise<{ status: string; message: string }> {
        try {
            const res = await fetch(`${API_BASE_URL}/analyze-site?site=${site}`, { method: 'POST' });
            if (!res.ok) throw new Error('Failed to start analysis');
            return await res.json();
        } catch (error) {
            console.error('API Error [analyzeSite]:', error);
            return { status: 'error', message: String(error) };
        }
    },

    async getSiteResult(site: 'benkmura' | 'debadihi'): Promise<SiteResult | null> {
        try {
            const res = await fetch(`${API_BASE_URL}/site-result/${site}`, { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to fetch site result');
            return await res.json();
        } catch (error) {
            console.error('API Error [getSiteResult]:', error);
            return null;
        }
    },

    async getSiteSurveys(site: 'benkmura' | 'debadihi'): Promise<SiteSurveyResponse | null> {
        try {
            const res = await fetch(`${API_BASE_URL}/site-surveys/${site}`, { cache: 'no-store' });
            if (!res.ok) throw new Error('Failed to fetch site surveys');
            return await res.json();
        } catch (error) {
            console.error('API Error [getSiteSurveys]:', error);
            return null;
        }
    },

    /**
     * Score the pipeline's casualties against an uploaded ground-truth file of
     * known dead locations (GeoJSON/CSV/KML/GPX) → recall + per-point hit/miss.
     * Returns { ok: false, error } on failure so the UI can show the reason.
     */
    async evaluateSite(
        site: 'benkmura' | 'debadihi',
        file: File,
        tol = 1.5,
    ): Promise<{ ok: true; result: EvalResult } | { ok: false; error: string }> {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('tol', String(tol));
            const res = await fetch(`${API_BASE_URL}/evaluate/${site}`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Evaluation failed' }));
                return { ok: false, error: err.detail || 'Evaluation failed' };
            }
            return { ok: true, result: await res.json() };
        } catch (error) {
            console.error('API Error [evaluateSite]:', error);
            return { ok: false, error: String(error) };
        }
    },
};