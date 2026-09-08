import { CheckCircle2, Database, Layers3, TriangleAlert } from "lucide-react";
import { Badge, Card, CardContent, CardHeader, CardTitle } from "@/components/ui/core";
import { useIndexStatus } from "@/lib/api";

function qdrantVariant(status: string) {
  const normalized = status.toLowerCase();
  return normalized === "ok" || normalized === "healthy" || normalized === "connected"
    ? "success"
    : normalized.includes("error") || normalized.includes("fail") || normalized.includes("down")
      ? "destructive"
      : "warning";
}

export default function Indexing() {
  const query = useIndexStatus();

  if (query.isLoading) {
    return <div data-testid="status-indexing-loading" className="py-20 text-center text-muted-foreground">Loading live indexing status…</div>;
  }

  if (query.isError) {
    return <div data-testid="status-indexing-api-error" className="border border-destructive/30 bg-destructive/5 p-5 text-sm">
      <p className="font-medium">Indexing status could not be loaded.</p>
      <p className="mt-1 text-muted-foreground">{query.error.message}</p>
      <button data-testid="button-retry-indexing-status" onClick={() => query.refetch()} className="mt-3 text-primary underline">Try again</button>
    </div>;
  }

  const status = query.data;
  if (!status) {
    return <div data-testid="status-indexing-empty" className="border border-border bg-card p-6 text-muted-foreground">No indexing status has been reported yet.</div>;
  }

  const metrics = [
    { label: "Indexed sources", value: status.indexed_sources, icon: CheckCircle2, color: "text-emerald-600", testId: "text-indexed-sources" },
    { label: "Index failures", value: status.index_failures, icon: TriangleAlert, color: "text-destructive", testId: "text-index-failures" },
  ];

  return <div className="space-y-8 animate-in fade-in duration-500">
    <div className="flex justify-between border-b border-border pb-6">
      <div>
        <h1 className="text-3xl font-serif">Indexing</h1>
        <p className="mt-2 font-medium text-muted-foreground">Live embedding and vector-store health for the archival catalog.</p>
      </div>
      <button data-testid="button-refresh-indexing-status" onClick={() => query.refetch()} className="self-start text-sm text-primary hover:underline">
        {query.isFetching ? "Refreshing…" : "Refresh"}
      </button>
    </div>

    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {metrics.map(({ label, value, icon: Icon, color, testId }) => <Card key={label}>
        <CardContent className="p-5">
          <div className="flex justify-between pb-3"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p><Icon className={`h-4 w-4 ${color}`} /></div>
          <p data-testid={testId} className="text-3xl font-serif font-bold">{value.toLocaleString()}</p>
        </CardContent>
      </Card>)}
    </div>

    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Layers3 className="h-4 w-4" />Embedding configuration</CardTitle></CardHeader>
        <CardContent className="space-y-4 text-sm">
          <StatusField label="Model" value={status.embedding_model} testId="text-embedding-model" />
          <StatusField label="Dimensions" value={status.embedding_dimensions.toLocaleString()} testId="text-embedding-dimensions" />
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Database className="h-4 w-4" />Qdrant</CardTitle></CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div><p className="mb-1 text-xs uppercase tracking-wider text-muted-foreground">Status</p><Badge data-testid="status-qdrant" variant={qdrantVariant(status.qdrant.status)}>{status.qdrant.status}</Badge></div>
          <StatusField label="Collection" value={status.qdrant.collection} testId="text-qdrant-collection" mono />
          <StatusField label="URL" value={status.qdrant.url} testId="text-qdrant-url" mono />
        </CardContent>
      </Card>
    </div>
  </div>;
}

function StatusField({ label, value, testId, mono = false }: { label: string; value: string; testId: string; mono?: boolean }) {
  return <div><p className="mb-1 text-xs uppercase tracking-wider text-muted-foreground">{label}</p><p data-testid={testId} className={mono ? "break-all font-mono text-xs" : ""}>{value || "Not reported"}</p></div>;
}