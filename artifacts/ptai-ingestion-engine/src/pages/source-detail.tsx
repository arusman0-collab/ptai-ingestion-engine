import { useParams, Link } from "wouter";
import { MOCK_SOURCES, MOCK_EVENTS } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, Badge, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/core";
import { ArrowLeft, HardDrive, FileText, Bot, Scale, Hash, Clock, CheckCircle2 } from "lucide-react";

export default function SourceDetail() {
  const { id } = useParams<{ id: string }>();
  const source = MOCK_SOURCES.find(s => s.id === id);
  const events = MOCK_EVENTS.filter(e => e.sourceId === id);

  if (!source) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-serif">Source Not Found</h2>
        <p className="text-muted-foreground mt-2">The requested ID {id} does not exist in the local dataset.</p>
        <Link href="/sources" className="text-primary hover:underline mt-4 inline-block">Return to Catalog</Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4 font-medium tracking-wide">
        <Link href="/sources" className="hover:text-foreground flex items-center gap-1 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Catalog
        </Link>
        <span>/</span>
        <span className="font-mono text-foreground">{source.id}</span>
      </div>

      <div className="border-b border-border pb-6 flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-serif text-foreground">{source.title}</h1>
            <Badge variant={source.archiveStatus === 'archived' ? 'success' : 'secondary'} className="text-xs">
              {source.archiveStatus.toUpperCase()}
            </Badge>
          </div>
          <p className="text-muted-foreground font-medium flex items-center gap-2">
            {source.speaker} <span className="opacity-50">•</span> {source.collection} <span className="opacity-50">•</span> {source.date}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Metadata & Provenance */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                <Hash className="w-4 h-4 text-muted-foreground" />
                Identity & Provenance
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Stable ID</div>
                <div className="font-mono text-primary font-medium">{source.id}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Publisher & Rights</div>
                <div className="flex items-center gap-2">
                  <span>{source.publisher}</span>
                  <Badge variant={source.rightsStatus === 'cleared' ? 'success' : 'warning'} className="text-[10px]">
                    {source.rightsStatus}
                  </Badge>
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Provenance Chain</div>
                <p className="text-muted-foreground leading-relaxed border-l-2 border-primary/20 pl-3 italic">
                  "{source.provenance}"
                </p>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">SHA-256 Checksum</div>
                <div className="font-mono text-[10px] bg-muted p-2 rounded-sm text-muted-foreground break-all">
                  {source.hashes.sha256}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-muted-foreground" />
                Storage Location
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Original Asset</div>
              <div className="font-mono text-[11px] text-foreground truncate" title={source.paths.original}>
                {source.paths.original}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Manifestations & Logs */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="pb-4 border-b border-border">
              <CardTitle className="text-base flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-muted-foreground" />
                  Derived Manifestations
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table className="border-0">
                <TableHeader className="bg-transparent">
                  <TableRow>
                    <TableHead className="pl-6">Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Provenance</TableHead>
                    <TableHead className="text-right pr-6">Path</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {source.manifestations.map((man) => (
                    <TableRow key={man.id}>
                      <TableCell className="pl-6">
                        <span className="font-medium text-foreground">{man.type.replace('_', ' ')}</span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={man.status === 'completed' ? 'success' : 'secondary'} className="text-[10px]">
                          {man.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {man.isAiDerived ? (
                          <span className="flex items-center gap-1.5 text-xs font-medium text-amber-700 bg-amber-500/10 px-2 py-1 rounded-sm w-fit border border-amber-600/20">
                            <Bot className="w-3 h-3" /> AI-Derived
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-xs font-medium text-primary bg-primary/10 px-2 py-1 rounded-sm w-fit border border-primary/20">
                            <Scale className="w-3 h-3" /> Exact Extraction
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-right pr-6">
                        <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[200px] inline-block" title={man.path}>
                          {man.path.split('/').pop()}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                  {source.manifestations.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center py-6 text-muted-foreground">
                        No manifestations generated yet.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-4 border-b border-border">
              <CardTitle className="text-base flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                Processing History
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {events.length > 0 ? (
                <Table className="border-0">
                  <TableBody>
                    {events.map((event) => (
                      <TableRow key={event.id}>
                        <TableCell className="pl-6 font-mono text-[11px] text-muted-foreground w-40">
                          {new Date(event.timestamp).toLocaleString(undefined, { timeStyle: 'short', dateStyle: 'short' })}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-foreground">{event.stage}</span>
                            <span className="text-xs text-muted-foreground font-mono">({event.transition})</span>
                          </div>
                          <div className="text-sm mt-1">{event.message}</div>
                        </TableCell>
                        <TableCell className="text-right pr-6">
                           <Badge variant={event.status === 'success' ? 'success' : event.status === 'error' ? 'destructive' : 'secondary'} className="text-[10px]">
                            {event.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="p-6 text-center text-muted-foreground text-sm">
                  No processing events recorded for this source.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
