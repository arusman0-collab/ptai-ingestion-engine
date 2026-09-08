import { useQuery } from "@tanstack/react-query";

export type LifecycleState =
  | "new" | "verified" | "approved" | "acquired" | "extracted" | "indexed"
  | "cataloged" | "duplicate" | "needs_review" | "rights_hold"
  | "extraction_failed" | "transcription_failed" | "indexing_failed" | "unavailable";

export interface SourceSummary {
  source_id: string; title: string | null; archive_status: LifecycleState;
  rights_status: string; source_type: string | null; updated_at: string;
}
export interface SourceRecord extends SourceSummary {
  speaker: string | null; author: string | null; date: string | null;
  publisher: string | null; platform: string | null; discovery_url: string | null;
  sha256: string | null; mime_type: string | null; file_size: number | null;
  created_at: string; notes: string | null; error_log: string | null;
}
export interface ProcessingEvent {
  id: number; created_at: string; source_id: string | null; pipeline_stage: string;
  previous_state: LifecycleState | null; new_state: LifecycleState | null; status: string;
  message: string | null; error: string | null;
}
export interface QueueItem {
  id: number; adapter: string; platform: string | null; title: string | null; url: string | null;
  possible_author: string | null; source_type: string | null; collection_slug: string;
  rights_status: string; status: LifecycleState; discovered_at: string; source_id: string | null; error: string | null;
}
export interface StatusGroup {
  total: number;
  by_status: Partial<Record<LifecycleState, number>>;
}
export interface StatusResponse { sources: StatusGroup; queue: StatusGroup; }
export interface QdrantStatus {
  status: string;
  collection: string;
  url: string;
}
export interface IndexStatusResponse {
  indexed_sources: number;
  index_failures: number;
  embedding_model: string;
  embedding_dimensions: number;
  qdrant: QdrantStatus;
}
export interface ListResponse<T> { items: T[]; total: number; }
export interface ReviewResponse { sources: SourceRecord[]; queue_candidates: QueueItem[]; total: number; }
export interface SourceDetailResponse { source: SourceRecord; events: ProcessingEvent[]; }

const artifactBase = import.meta.env.BASE_URL.replace(/\/$/, "");
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? `${artifactBase}/ptai-api`;
async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json() as Promise<T>;
}
const liveQuery = { staleTime: 15_000, refetchInterval: 30_000, refetchIntervalInBackground: false, retry: 1 };
export const useStatus = () => useQuery({ queryKey: ["status"], queryFn: () => get<StatusResponse>("/api/status"), ...liveQuery });
export const useIndexStatus = () => useQuery({ queryKey: ["index-status"], queryFn: () => get<IndexStatusResponse>("/api/index/status"), ...liveQuery });
export const useSources = () => useQuery({ queryKey: ["sources"], queryFn: () => get<ListResponse<SourceSummary>>("/api/sources"), ...liveQuery });
export const useSource = (id?: string) => useQuery({ queryKey: ["source", id], queryFn: () => get<SourceDetailResponse>(`/api/sources/${encodeURIComponent(id!)}`), enabled: !!id, ...liveQuery });
export const useQueue = () => useQuery({ queryKey: ["queue"], queryFn: () => get<ListResponse<QueueItem>>("/api/queue"), ...liveQuery });
export const useReview = () => useQuery({ queryKey: ["review"], queryFn: () => get<ReviewResponse>("/api/review"), ...liveQuery });

export const lifecycleLabel = (state: LifecycleState | string) => ({
  new: "New", verified: "Verified", approved: "Approved", acquired: "Acquired",
  extracted: "Extracted", indexed: "Indexed", cataloged: "Cataloged", duplicate: "Duplicate",
  needs_review: "Needs review", rights_hold: "Rights hold", extraction_failed: "Extraction failed",
  transcription_failed: "Transcription failed", indexing_failed: "Indexing failed", unavailable: "Unavailable",
}[state] ?? state);

export const lifecycleVariant = (state: string) =>
  state === "cataloged" ? "success" : state.includes("failed") ? "destructive" :
  state === "rights_hold" ? "warning" : "secondary";