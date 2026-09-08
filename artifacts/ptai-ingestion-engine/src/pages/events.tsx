import { MOCK_EVENTS } from "@/lib/data";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge } from "@/components/ui/core";
import { Link } from "wouter";

export default function Events() {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-border pb-6">
        <h1 className="text-3xl font-serif text-foreground">Audit Events</h1>
        <p className="text-muted-foreground mt-2 font-medium">Immutable log of system transitions, failures, and operator actions.</p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Timestamp (UTC)</TableHead>
            <TableHead>Source Ref</TableHead>
            <TableHead>Subsystem Stage</TableHead>
            <TableHead>State Transition</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Message Payload</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {MOCK_EVENTS.map((event) => (
            <TableRow key={event.id}>
              <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                {event.timestamp}
              </TableCell>
              <TableCell>
                <Link href={`/sources/${event.sourceId}`} className="font-mono text-xs font-semibold text-primary hover:underline">
                  {event.sourceId}
                </Link>
              </TableCell>
              <TableCell>
                <span className="text-xs font-bold uppercase tracking-wider text-foreground">{event.stage}</span>
              </TableCell>
              <TableCell>
                <span className="font-mono text-[11px] text-muted-foreground">{event.transition}</span>
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
              <TableCell className="text-sm">
                {event.message}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
