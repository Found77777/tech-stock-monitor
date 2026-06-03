import type { Metadata } from "next";
import Link from "next/link";
import { Activity, BarChart3, BookOpenCheck, ClipboardList, Gauge, Newspaper, ScrollText } from "lucide-react";
import { WorkbenchHeader } from "@/components/workbench-header";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tech Stock Monitor",
  description: "A-share technology stock monitoring workstation",
};

const nav = [
  ["/", "Dashboard", Activity],
  ["/enhanced-watchlist", "Enhanced Watchlist", Gauge],
  ["/daily-review", "Daily Review", BookOpenCheck],
  ["/trade-plan", "Trade Plan", ClipboardList],
  ["/trade-log", "Trade Log", ScrollText],
  ["/plan-drift", "Plan Drift", BarChart3],
  ["/review-stats", "Review Stats", BarChart3],
  ["/ai-review-summary", "AI Review", Newspaper],
] as const;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="dark">
      <body className="trader-grid min-h-screen">
        <div className="flex min-h-screen">
          <aside className="hidden w-72 border-r border-border/70 bg-slate-950/85 p-5 backdrop-blur lg:block">
            <div className="mb-8">
              <div className="text-xl font-bold text-primary">A股科技监控</div>
              <div className="text-xs text-muted-foreground">Trader Research Workbench</div>
            </div>
            <nav className="space-y-2">
              {nav.map(([href, label, Icon]) => (
                <Link key={href} href={href} className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-accent hover:text-white">
                  <Icon className="h-4 w-4" /> {label}
                </Link>
              ))}
            </nav>
          </aside>
          <main className="flex-1 p-4 lg:p-8">
            <div className="mx-auto max-w-[1440px]">
              <WorkbenchHeader />
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
