"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import { ChevronRight, Database } from "lucide-react";

import { apiPaths, fetcher } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { TimeseriesPoint } from "@/types";

const CRUMB_LABELS: Record<string, string> = {
  "": "ダッシュボード",
  rankings: "動画ランキング",
  compare: "比較分析",
  videos: "動画",
};

function buildCrumbs(pathname: string) {
  if (pathname === "/" || pathname === "") {
    return [{ href: "/", label: "ダッシュボード" }];
  }
  const parts = pathname.split("/").filter(Boolean);
  const crumbs: { href: string; label: string }[] = [
    { href: "/", label: "ホーム" },
  ];
  let acc = "";
  parts.forEach((p, i) => {
    acc += `/${p}`;
    const label =
      CRUMB_LABELS[p] ??
      (i === parts.length - 1 ? p : decodeURIComponent(p));
    crumbs.push({ href: acc, label });
  });
  return crumbs;
}

export function TopBar() {
  const pathname = usePathname();
  const crumbs = buildCrumbs(pathname);

  // Latest collection date drives the freshness indicator.
  const { data: subsSeries } = useSWR<TimeseriesPoint[]>(
    apiPaths.channelTimeseries("subscriber_count"),
    fetcher
  );
  const lastCollected = subsSeries && subsSeries.length > 0
    ? [...subsSeries].sort((a, b) =>
        b.collected_at.localeCompare(a.collected_at)
      )[0]?.collected_at
    : undefined;

  return (
    <header
      className="sticky top-0 z-20 flex items-center gap-4 border-b border-[color:var(--border)] bg-[color:var(--surface)]/85 px-8 backdrop-blur-md"
      style={{ height: "var(--topbar-h)" }}
    >
      <nav
        aria-label="Breadcrumb"
        className="flex items-center gap-1.5 text-[12.5px] text-[color:var(--muted-foreground)]"
      >
        {crumbs.map((c, i) => {
          const last = i === crumbs.length - 1;
          return (
            <span key={c.href} className="flex items-center gap-1.5">
              {i > 0 && <ChevronRight className="h-3.5 w-3.5 opacity-60" />}
              {last ? (
                <span className="font-semibold text-[color:var(--foreground)]">
                  {c.label}
                </span>
              ) : (
                <Link
                  href={c.href}
                  className="hover:text-[color:var(--foreground)]"
                >
                  {c.label}
                </Link>
              )}
            </span>
          );
        })}
      </nav>

      <div className="flex-1" />

      {lastCollected && (
        <div className="hidden items-center gap-2 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] px-3 py-1.5 text-[12px] text-[color:var(--muted-foreground)] sm:inline-flex">
          <Database className="h-3.5 w-3.5" />
          最終収集{" "}
          <span className="font-num text-[color:var(--foreground)]">
            {formatDate(lastCollected)}
          </span>
        </div>
      )}
    </header>
  );
}
