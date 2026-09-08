import { useState } from "react";
import { Link } from "wouter";
import { MOCK_SOURCES } from "@/lib/data";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge, Button } from "@/components/ui/core";
import { Search, Filter } from "lucide-react";

export default function Sources() {
  const [search, setSearch] = useState("");

  const filteredSources = MOCK_SOURCES.filter(s => 
    s.id.toLowerCase().includes(search.toLowerCase()) || 
    s.title.toLowerCase().includes(search.toLowerCase()) ||
    s.collection.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="border-b border-border pb-6">
        <h1 className="text-3xl font-serif text-foreground">Canonical Catalog</h1>
        <p className="text-muted-foreground mt-2 font-medium">Searchable registry of preserved scholarly sources.</p>
      </div>

      <div className="flex gap-4 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search by ID, title, or collection..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-10 pl-9 pr-4 rounded-sm border border-border bg-card text-sm focus:outline-none focus:ring-1 focus:ring-primary font-mono placeholder:font-sans"
          />
        </div>
        <Button variant="outline" className="gap-2">
          <Filter className="h-4 w-4" />
          Filter
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Stable ID</TableHead>
            <TableHead>Title</TableHead>
            <TableHead>Collection</TableHead>
            <TableHead>Format</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredSources.map((source) => (
            <TableRow key={source.id}>
              <TableCell className="font-mono text-xs font-semibold text-primary">
                {source.id}
              </TableCell>
              <TableCell>
                <div className="font-medium text-foreground">{source.title}</div>
                <div className="text-xs text-muted-foreground mt-1">{source.date} • {source.speaker}</div>
              </TableCell>
              <TableCell>
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{source.collection}</span>
              </TableCell>
              <TableCell>
                <Badge variant="outline" className="text-[10px] uppercase">{source.type}</Badge>
              </TableCell>
              <TableCell>
                <div className="flex flex-col gap-1 items-start">
                  <Badge variant={source.archiveStatus === 'archived' ? 'success' : 'secondary'} className="text-[10px]">
                    {source.archiveStatus}
                  </Badge>
                  {source.rightsStatus === 'hold' && (
                    <Badge variant="warning" className="text-[10px]">Rights Hold</Badge>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-right">
                <Link href={`/sources/${source.id}`} className="inline-flex items-center justify-center whitespace-nowrap rounded-sm text-xs font-medium transition-colors border border-border bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-8 px-3">
                  Inspect
                </Link>
              </TableCell>
            </TableRow>
          ))}
          {filteredSources.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                No sources found matching "{search}"
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
