"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  GitCompareArrows,
  LayoutDashboard,
  ListOrdered,
} from "lucide-react";

import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  end?: boolean;
}

const REPORTS: NavItem[] = [
  { href: "/", label: "ダッシュボード", icon: LayoutDashboard, end: true },
  { href: "/rankings", label: "動画ランキング", icon: ListOrdered },
  { href: "/compare", label: "比較分析", icon: GitCompareArrows },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="fixed inset-y-0 left-0 z-30 flex flex-col border-r border-[color:var(--border)] bg-[color:var(--surface)]"
      style={{ width: "var(--sidebar-w)" }}
    >
      <div className="flex h-[var(--topbar-h)] items-center gap-2.5 border-b border-[color:var(--border)] px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--foreground)] text-white">
          <Activity className="h-4 w-4" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
            YouTube
          </span>
          <span className="font-display text-[15px]">Analytics</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5">
        <SectionLabel>レポート</SectionLabel>
        <ul className="mt-1.5 space-y-0.5">
          {REPORTS.map((item) => {
            const active = item.end
              ? pathname === item.href
              : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors",
                    active
                      ? "bg-[color:var(--primary-soft)] text-[color:var(--primary)]"
                      : "text-[color:var(--muted-foreground)] hover:bg-[color:var(--surface-2)] hover:text-[color:var(--foreground)]"
                  )}
                >
                  {active && (
                    <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-[color:var(--primary)]" />
                  )}
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-[color:var(--border)] p-4 text-[10.5px] font-medium uppercase tracking-[0.14em] text-[color:var(--muted-foreground)]">
        v0.1.0
      </div>
    </aside>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-2.5 text-[10.5px] font-semibold uppercase tracking-[0.16em] text-[color:var(--muted-foreground)]">
      {children}
    </div>
  );
}
