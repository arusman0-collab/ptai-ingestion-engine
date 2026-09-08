import { AlertCircle, CheckCircle, FileText, Search } from "lucide-react";
import { Badge, Card, CardContent, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/core";
import { lifecycleLabel, lifecycleVariant, useStatus } from "@/lib/api";

export default function Home() {
  const { data, isLoading, isError, error, refetch, isFetching } = useStatus();
  const counts = data?.sources.by_status ?? {};
  const metrics = [
    { state: "new", icon: Search, color: "text-primary" }, { state: "needs_review", icon: AlertCircle, color: "text-destructive" },
    { state: "rights_hold", icon: AlertCircle, color: "text-amber-600" }, { state: "cataloged", icon: CheckCircle, color: "text-emerald-600" },
    { state: "extracted", icon: FileText, color: "text-muted-foreground" },
  ];
  return <div className="space-y-8 animate-in fade-in duration-500">
    <div className="border-b border-border pb-6 flex justify-between"><div><h1 className="text-3xl font-serif">Pipeline Overview</h1><p className="text-muted-foreground mt-2 font-medium">Live SQLite catalog and discovery queue status.</p></div><button data-testid="button-refresh-status" onClick={() => refetch()} className="text-sm text-primary hover:underline">{isFetching ? "Refreshing…" : "Refresh"}</button></div>
    {isError ? <ErrorMessage error={error} retry={refetch} /> : <><div className="grid grid-cols-1 md:grid-cols-5 gap-4">{metrics.map(({ state, icon: Icon, color }) => <Card key={state}><CardContent className="p-5"><div className="flex justify-between pb-3"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{lifecycleLabel(state)}</p><Icon className={`h-4 w-4 ${color}`} /></div><div data-testid={`text-lifecycle-count-${state}`} className="text-3xl font-serif font-bold">{isLoading ? "—" : (counts[state as keyof typeof counts] ?? 0).toLocaleString()}</div></CardContent></Card>)}</div>
      <div className="space-y-4 pt-4"><h2 className="text-xl font-serif">Queue Status</h2><Table><TableHeader><TableRow><TableHead>Lifecycle state</TableHead><TableHead className="text-right">Candidates</TableHead></TableRow></TableHeader><TableBody>{isLoading ? <LoadingRows columns={2} /> : data?.queue.total ? Object.entries(data.queue.by_status).map(([status, count]) => <TableRow key={status}><TableCell><Badge variant={lifecycleVariant(status)}>{lifecycleLabel(status)}</Badge></TableCell><TableCell className="text-right font-mono">{count}</TableCell></TableRow>) : <EmptyRow columns={2} message="No discovery candidates are currently recorded." />}</TableBody></Table></div></>}
  </div>;
}
export function ErrorMessage({ error, retry }: { error: Error | null; retry: () => void }) { return <div data-testid="status-api-error" className="border border-destructive/30 bg-destructive/5 p-5 text-sm"><p className="font-medium">Live data could not be loaded.</p><p className="text-muted-foreground mt-1">{error?.message ?? "Unknown API error"}</p><button data-testid="button-retry-api" onClick={retry} className="text-primary underline mt-3">Try again</button></div>; }
export function LoadingRows({ columns }: { columns: number }) { return <TableRow><TableCell colSpan={columns} className="py-8 text-center text-muted-foreground">Loading live data…</TableCell></TableRow>; }
export function EmptyRow({ columns, message }: { columns: number; message: string }) { return <TableRow><TableCell colSpan={columns} className="py-8 text-center text-muted-foreground">{message}</TableCell></TableRow>; }