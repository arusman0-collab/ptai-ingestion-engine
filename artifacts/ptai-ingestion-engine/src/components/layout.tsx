import { Link, useLocation } from "wouter";
import { BookOpen, Database, Inbox, Activity } from "lucide-react";
import { cn } from "@/components/ui/core";

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();

  const navItems = [
    { href: "/", label: "Overview", icon: Activity },
    { href: "/queue", label: "Discovery Queue", icon: Inbox },
    { href: "/sources", label: "Canonical Catalog", icon: BookOpen },
    { href: "/events", label: "Audit Events", icon: Database },
  ];

  return (
    <div className="min-h-[100dvh] bg-background flex text-foreground font-sans">
      <aside className="w-64 border-r border-border bg-card flex flex-col shrink-0">
        <div className="p-6 border-b border-border">
          <div className="font-serif text-xl font-bold tracking-tight text-primary">PT-AI Engine</div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground mt-1 font-mono">Provenance Console</div>
        </div>
        <nav className="flex-1 py-6 flex flex-col gap-1 px-4">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground mb-3 px-2">Operations</div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location === item.href || (item.href !== "/" && location.startsWith(item.href));
            return (
              <Link key={item.href} href={item.href} className={cn(
                "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-sm transition-colors",
                isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}>
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-border">
          <div className="text-xs text-muted-foreground bg-muted p-3 rounded-sm border border-border/50 shadow-inner">
            <span className="font-semibold text-foreground block mb-1">Phase 1 Live Data</span>
            Connected to the operator API. Data refreshes every 30 seconds.
          </div>
        </div>
      </aside>
      <main className="flex-1 flex flex-col h-[100dvh] overflow-hidden bg-background">
        <div className="flex-1 overflow-auto p-8 lg:p-12">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
