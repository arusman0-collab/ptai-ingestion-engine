import { useState } from "react";
import { MOCK_QUEUE_CANDIDATES } from "@/lib/data";
import { Card, CardContent, CardHeader, CardTitle, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge, Button } from "@/components/ui/core";
import { Check, X, Clock } from "lucide-react";

export default function Queue() {
  const [candidates, setCandidates] = useState(MOCK_QUEUE_CANDIDATES);

  const handleAction = (id: string, action: 'approve' | 'reject') => {
    setCandidates(candidates.filter(c => c.id !== id));
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-border pb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-serif text-foreground">Discovery Queue</h1>
          <p className="text-muted-foreground mt-2 font-medium">Candidates blocked awaiting human review or rights clearance.</p>
        </div>
        <Badge variant="warning" className="text-sm px-3 py-1">
          {candidates.length} Pending
        </Badge>
      </div>

      {candidates.length === 0 ? (
        <Card className="border-dashed bg-muted/20">
          <CardContent className="flex flex-col items-center justify-center p-12 text-center">
            <Check className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <h3 className="text-lg font-serif font-medium">Queue is empty</h3>
            <p className="text-sm text-muted-foreground mt-1">All discovery candidates have been processed.</p>
          </CardContent>
        </Card>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Candidate</TableHead>
              <TableHead>Platform / Origin</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {candidates.map((candidate) => (
              <TableRow key={candidate.id}>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {candidate.id}
                </TableCell>
                <TableCell>
                  <div className="font-medium text-foreground">{candidate.title}</div>
                  <div className="text-xs text-muted-foreground mt-1 font-mono truncate max-w-[250px]" title={candidate.url}>
                    {candidate.url}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-semibold uppercase tracking-wider">{candidate.platform}</span>
                    <span className="text-xs text-muted-foreground font-mono">{candidate.adapter}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={candidate.status === 'rights_hold' ? 'warning' : 'secondary'}>
                    {candidate.status.replace('_', ' ')}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={() => handleAction(candidate.id, 'reject')} className="h-8 px-2 hover:border-destructive hover:text-destructive">
                      <X className="h-4 w-4" />
                    </Button>
                    <Button variant="default" size="sm" onClick={() => handleAction(candidate.id, 'approve')} className="h-8 px-3">
                      Clear & Ingest
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
