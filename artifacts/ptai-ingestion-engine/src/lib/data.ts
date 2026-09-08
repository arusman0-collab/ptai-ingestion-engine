// Sample Data for ST-000001, ST-000002, ST-000003
export interface Source {
  id: string;
  collection: string;
  title: string;
  speaker: string;
  date: string;
  datePrecision: 'day' | 'month' | 'year';
  language: string;
  type: 'video' | 'audio' | 'text';
  publisher: string;
  sourceLevel: 'canonical' | 'derivative';
  rightsStatus: 'cleared' | 'hold' | 'pending';
  archiveStatus: 'archived' | 'processing' | 'failed';
  hashes: { sha256: string };
  paths: { original: string; processed?: string };
  reviewStatus: 'verified' | 'needs_review' | 'approved';
  manifestations: Manifestation[];
  provenance: string;
}

export interface Manifestation {
  id: string;
  type: 'transcript_original' | 'transcript_translated' | 'summary_ai' | 'audio_extracted';
  status: 'completed' | 'processing' | 'failed';
  path: string;
  isAiDerived: boolean;
}

export const MOCK_LIFECYCLE_COUNTS = {
  new: 3,
  verified: 2,
  approved: 1,
  acquired: 1,
  extracted: 1,
  indexed: 0,
  cataloged: 1,
  failed: 1,
  needs_review: 1,
  rights_hold: 1
};

export const MOCK_QUEUE_CANDIDATES = [
  {
    id: "cand-101",
    platform: "local_drop",
    adapter: "local_drop",
    title: "Filsafat Asia: Bagian 34",
    url: "file://./data/drop/filsafat-asia-34.html",
    speaker: "Rev. Stephen Tong",
    sourceType: "html",
    status: "needs_review",
    discoveryMetadata: { discoveredAt: "2023-10-01T10:00:00Z", reason: "Authorship metadata requires confirmation" }
  },
  {
    id: "cand-102",
    platform: "local_drop",
    adapter: "local_drop",
    title: "Seminar archive scan",
    url: "file://./data/drop/seminar-scan.pdf",
    speaker: "Rev. Stephen Tong",
    sourceType: "pdf",
    status: "rights_hold",
    discoveryMetadata: { discoveredAt: "2023-10-02T14:30:00Z", reason: "Archival permission not yet recorded" }
  },
  {
    id: "cand-103",
    platform: "local_drop",
    adapter: "local_drop",
    title: "Unlabeled sermon transcript",
    url: "file://./data/drop/unlabeled-transcript.txt",
    speaker: "Rev. Stephen Tong",
    sourceType: "text",
    status: "needs_review",
    discoveryMetadata: { discoveredAt: "2023-10-05T08:15:00Z", reason: "Speaker identity is uncertain" }
  }
];

export const MOCK_SOURCES: Source[] = [
  {
    id: "ST-000001",
    collection: "Stephen Tong",
    title: "Filsafat Asia: Bagian 1",
    speaker: "Rev. Stephen Tong",
    date: "2008-01-01",
    datePrecision: "day",
    language: "id",
    type: "text",
    publisher: "Buletin PILLAR",
    sourceLevel: "canonical",
    rightsStatus: "cleared",
    archiveStatus: "archived",
    hashes: { sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" },
    paths: { original: "./data/original/ST-000001/source.html", processed: "./data/processed/ST-000001.txt" },
    reviewStatus: "approved",
    provenance: "Development fixture representing an existing catalog record. No production record was imported.",
    manifestations: [
      { id: "man-1", type: "transcript_original", status: "completed", path: "./data/processed/ST-000001.txt", isAiDerived: false },
    ]
  },
  {
    id: "ST-000002",
    collection: "Stephen Tong",
    title: "Filsafat Asia: Bagian 32",
    speaker: "Rev. Stephen Tong",
    date: "2008-01-01",
    datePrecision: "month",
    language: "id",
    type: "text",
    publisher: "Buletin PILLAR",
    sourceLevel: "canonical",
    rightsStatus: "hold",
    archiveStatus: "processing",
    hashes: { sha256: "8a9b3c4d5e6f7g8h9i0j1k2l3m4n5o6p" },
    paths: { original: "./data/original/ST-000002/source.html" },
    reviewStatus: "needs_review",
    provenance: "Development fixture. Automation is stopped until rights are explicitly cleared.",
    manifestations: []
  },
  {
    id: "ST-000003",
    collection: "Stephen Tong",
    title: "Filsafat Asia: Bagian 33",
    speaker: "Rev. Stephen Tong",
    date: "2008-01-01",
    datePrecision: "year",
    language: "id",
    type: "text",
    publisher: "Buletin PILLAR",
    sourceLevel: "derivative",
    rightsStatus: "pending",
    archiveStatus: "failed",
    hashes: { sha256: "112233445566778899aabbccddeeff" },
    paths: { original: "./data/original/ST-000003/source.html" },
    reviewStatus: "needs_review",
    provenance: "Development fixture. Metadata conflict is retained for human review.",
    manifestations: []
  }
];

export const MOCK_EVENTS = [
  { id: "evt-1", timestamp: "2023-10-05T08:12:00Z", sourceId: "ST-000001", stage: "extraction", transition: "acquired -> extracted", status: "success", elapsed: "2s", message: "Meaningful HTML text preserved as a derived artifact." },
  { id: "evt-2", timestamp: "2023-10-05T09:00:00Z", sourceId: "ST-000001", stage: "catalog", transition: "extracted -> cataloged", status: "success", elapsed: "1s", message: "Source cataloged with SHA-256 and provenance metadata." },
  { id: "evt-3", timestamp: "2023-10-05T09:05:00Z", sourceId: "ST-000002", stage: "rights_check", transition: "new -> rights_hold", status: "blocked", elapsed: "1s", message: "Automation stopped: archival permission is not explicit." },
  { id: "evt-4", timestamp: "2023-10-05T10:15:00Z", sourceId: "ST-000003", stage: "verification", transition: "new -> needs_review", status: "error", elapsed: "1s", message: "Metadata conflict retained for human review; no merge was performed." },
];