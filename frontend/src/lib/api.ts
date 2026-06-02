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
    gemini_analysis?: string;
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
            const res = await fetch(`${API_BASE_URL}/stats`);
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
            const res = await fetch(`${API_BASE_URL}/patches`);
            if (!res.ok) throw new Error('Failed to fetch patches');
            return await res.json();
        } catch (error) {
            console.error('API Error [getPatches]:', error);
            return [];
        }
    },

    async getPatchDetails(patchId: string): Promise<PatchData | null> {
        try {
            const res = await fetch(`${API_BASE_URL}/patch/${encodeURIComponent(patchId)}`);
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
            const res = await fetch(`${API_BASE_URL}/patches/all`);
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
        patchName: string
    ): Promise<{ task_id: string; status: string } | null> {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('patch_name', patchName);

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
            const res = await fetch(`${API_BASE_URL}/task-status/${taskId}`);
            if (!res.ok) throw new Error('Failed to get task status');
            return await res.json();
        } catch (error) {
            console.error('API Error [getTaskStatus]:', error);
            return null;
        }
    },

    /** Returns the full URL to an uploaded image served from /api/uploads/<filename> */
    getImageUrl(filename: string): string {
        // API_BASE_URL is e.g. http://127.0.0.1:8000/api
        // Static mounts are at http://127.0.0.1:8000/api/uploads/<filename>
        return `${API_BASE_URL}/uploads/${filename}`;
    },
};