import { useState } from "react";
import { Link } from "wouter";
import { Search } from "lucide-react";
import { Badge, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/core";
import { lifecycleLabel, lifecycleVariant, useSources } from "@/lib/api";
import { EmptyRow, ErrorMessage, LoadingRows } from "./home";

export default function Sources() {
  const [search, setSearch] = useState(""); const query = useSources();
  const sources = (query.data?.items ?? []).filter(source => [source.source_id, source.title, source.source_type].some(value => value?.toLowerCase().includes(search.toLowerCase())));
  return <div className="space-y-8 animate-in fade-in duration-500"><div className="border-b border-border pb-6"><h1 className="text-3xl font-serif">Canonical Catalog</h1><p className="text-muted-foreground mt-2 font-medium">Live registry of preserved scholarly sources.</p></div>
    <div className="relative max-w-md"><Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" /><input data-testid="input-search-sources" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search by ID, title, or format…" className="w-full h-10 pl-9 pr-4 rounded-sm border border-border bg-card text-sm" /></div>
    {query.isError ? <ErrorMessage error={query.error} retry={query.refetch} /> : <Table><TableHeader><TableRow><TableHead>Stable ID</TableHead><TableHead>Title</TableHead><TableHead>Format</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Action</TableHead></TableRow></TableHeader><TableBody>{query.isLoading ? <LoadingRows columns={5} /> : sources.length ? sources.map(source => <TableRow key={source.source_id}><TableCell className="font-mono text-xs font-semibold text-primary">{source.source_id}</TableCell><TableCell><div className="font-medium">{source.title ?? "Untitled source"}</div><div className="text-xs text-muted-foreground mt-1">{source.updated_at}</div></TableCell><TableCell><Badge variant="outline">{source.source_type ?? "unknown"}</Badge></TableCell><TableCell><Badge variant={lifecycleVariant(source.archive_status)}>{lifecycleLabel(source.archive_status)}</Badge></TableCell><TableCell className="text-right"><Link data-testid={`link-inspect-source-${source.source_id}`} href={`/sources/${source.source_id}`} className="text-primary text-sm hover:underline">Inspect</Link></TableCell></TableRow>) : <EmptyRow columns={5} message={search ? `No live sources match “${search}”.` : "No sources have been cataloged yet."} />}</TableBody></Table>}
  </div>;
}