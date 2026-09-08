import { MOCK_LIFECYCLE_COUNTS, MOCK_EVENTS } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge } from "@/components/ui/core";
import { AlertCircle, CheckCircle, Database, Search, FileText } from "lucide-react";

export default function Home() {
  const metrics = [
    { label: "Discovered", value: MOCK_LIFECYCLE_COUNTS.new, icon: Search, color: "text-primary" },
    { label: "Needs Review", value: MOCK_LIFECYCLE_COUNTS.needs_review, icon: AlertCircle, color: "text-destructive", alert: true },
    { label: "Rights Hold", value: MOCK_LIFECYCLE_COUNTS.rights_hold, icon: AlertCircle, color: "text-amber-600", alert: true },
    { label: "Cataloged", value: MOCK_LIFECYCLE_COUNTS.cataloged, icon: CheckCircle, color: "text-emerald-600" },
    { label: "Extracted", value: MOCK_LIFECYCLE_COUNTS.extracted, icon: FileText, color: "text-muted-foreground" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-border pb-6">
        <h1 className="text-3xl font-serif text-foreground">Pipeline Overview</h1>
        <p className="text-muted-foreground mt-2 font-medium">Global ingestion status and recent activity logs.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {metrics.map((m) => (
          <Card key={m.label} className={m.alert ? "border-amber-200 bg-amber-50/30" : ""}>
            <CardContent className="p-5">
              <div className="flex items-center justify-between space-y-0 pb-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{m.label}</p>
                <m.icon className={`h-4 w-4 ${m.color}`} />
              </div>
              <div className="text-3xl font-serif font-bold text-foreground">{m.value.toLocaleString()}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="space-y-4 pt-4">
        <h2 className="text-xl font-serif text-foreground">Recent Audit Events</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Timestamp</TableHead>
              <TableHead>Source ID</TableHead>
              <TableHead>Stage</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Message</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {MOCK_EVENTS.map((event) => (
              <TableRow key={event.id}>
                <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                  {new Date(event.timestamp).toLocaleString()}
                </TableCell>
                <TableCell className="font-mono text-xs font-medium text-foreground">
                  {event.sourceId}
                </TableCell>
                <TableCell>
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{event.stage}</span>
                </TableCell>
                <TableCell>
                  <Badge variant={
                    event.status === 'success' ? 'success' :
                    event.status === 'error' ? 'destructive' :
                    event.status === 'blocked' ? 'warning' : 'secondary'
                  }>
                    {event.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-foreground max-w-md truncate" title={event.message}>
                  {event.message}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
