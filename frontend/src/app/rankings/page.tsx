"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { ArrowUpRight, BarChart3, Crown, ListOrdered } from "lucide-react";

import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiPaths, fetcher } from "@/lib/api";
import { cn, formatCompact, formatDate, formatNumber } from "@/lib/utils";
import type { MetricKey, RankingItem } from "@/types";

type Days = "7" | "30" | "60" | "90";

const METRICS: { value: MetricKey; label: string; unit?: string }[] = [
  { value: "views", label: "再生数", unit: "回" },
  {
    value: "estimatedMinutesWatched",
    label: "総視聴時間",
    unit: "分",
  },
  {
    value: "averageViewPercentage",
    label: "平均視聴維持率",
    unit: "%",
  },
];

const DAYS: { value: Days; label: string }[] = [
  { value: "7", label: "7D" },
  { value: "30", label: "30D" },
  { value: "60", label: "60D" },
  { value: "90", label: "90D" },
];

export default function RankingsPage() {
  const [metric, setMetric] = useState<MetricKey>("views");
  const [days, setDays] = useState<Days>("30");

  const { data, isLoading, error } = useSWR<RankingItem[]>(
    apiPaths.rankings(metric, 20, Number(days)),
    fetcher
  );

  const items = data ?? [];
  const max = useMemo(() => Math.max(...items.map((r) => r.value), 1), [items]);
  const total = useMemo(
    () => items.reduce((s, r) => s + r.value, 0),
    [items]
  );
  const topThree = items.slice(0, 3);
  const metricMeta = METRICS.find((m) => m.value === metric);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Performance ranking"
        title="動画ランキング"
        description="期間と指標を切り替えて、勢いのある動画を見つけます。"
        actions={
          <SegmentedControl
            value={days}
            onChange={setDays}
            options={DAYS}
            label="期間"
          />
        }
      />

      {/* Metric tabs */}
      <div className="flex flex-wrap items-center gap-2">
        {METRICS.map((m) => {
          const active = m.value === metric;
          return (
            <button
              key={m.value}
              onClick={() => setMetric(m.value)}
              className={cn(
                "group flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[12.5px] font-semibold transition-all",
                active
                  ? "border-[color:var(--primary)] bg-[color:var(--primary)] text-white shadow-[0_4px_12px_-4px_rgba(26,115,232,0.45)]"
                  : "border-[color:var(--border)] bg-[color:var(--surface)] text-[color:var(--muted-foreground)] hover:border-[color:var(--border-strong)] hover:text-[color:var(--foreground)]"
              )}
            >
              {m.label}
              {active && (
                <span className="rounded-full bg-white/15 px-1.5 py-0.5 text-[10px] font-medium">
                  {m.unit ?? ""}
                </span>
              )}
            </button>
          );
        })}
        <div className="ml-auto flex items-center gap-3 text-[11px] text-[color:var(--muted-foreground)]">
          <span className="hidden items-center gap-1.5 md:inline-flex">
            <BarChart3 className="h-3.5 w-3.5" />
            集計対象 {items.length} 本
          </span>
          <span className="hidden items-center gap-1.5 lg:inline-flex">
            合計{" "}
            <span className="font-num text-[color:var(--foreground)]">
              {formatNumber(total)}
            </span>
          </span>
        </div>
      </div>

      {/* Top 3 podium */}
      {topThree.length > 0 && (
        <section className="grid gap-4 md:grid-cols-3">
          {topThree.map((r, i) => (
            <PodiumCard
              key={r.video_id}
              item={r}
              rank={r.rank}
              max={max}
              unit={metricMeta?.unit}
              delay={i * 100}
            />
          ))}
        </section>
      )}

      {/* Ranking table */}
      <Panel
        eyebrow="Full leaderboard"
        title="ランキングテーブル"
        description={`${metricMeta?.label ?? metric} ・ 直近 ${days} 日`}
        bodyPadding={false}
      >
        {error ? (
          <div className="px-5 py-10">
            <EmptyState
              title="取得失敗"
              message="バックエンドのレスポンスが取得できませんでした。"
            />
          </div>
        ) : isLoading ? (
          <div className="space-y-2 p-5">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton h-10 w-full" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="p-5">
            <EmptyState message="該当する動画がありません" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14">#</TableHead>
                <TableHead>タイトル</TableHead>
                <TableHead className="w-32">公開日</TableHead>
                <TableHead className="w-[28%]">分布</TableHead>
                <TableHead className="w-32 text-right">値</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((r) => {
                const ratio = (r.value / max) * 100;
                return (
                  <TableRow key={r.video_id}>
                    <TableCell>
                      <div className="font-num text-[12.5px] text-[color:var(--muted-foreground)]">
                        {r.rank.toString().padStart(2, "0")}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/videos/${r.video_id}`}
                        className="group inline-flex items-center gap-2 text-[13px] font-medium text-[color:var(--foreground)] hover:text-[color:var(--primary)]"
                      >
                        <span className="line-clamp-1">{r.title}</span>
                        <ArrowUpRight className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
                      </Link>
                    </TableCell>
                    <TableCell className="text-[12px] text-[color:var(--muted-foreground)]">
                      {formatDate(r.published_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-[color:var(--surface-2)]">
                          <div
                            className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-[color:var(--primary)] to-[color:var(--accent)]"
                            style={{ width: `${ratio}%` }}
                          />
                        </div>
                        <span className="font-num shrink-0 text-[10.5px] text-[color:var(--muted-foreground)]">
                          {ratio.toFixed(0)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className="font-num text-[13.5px] text-[color:var(--foreground)]">
                        {formatNumber(r.value)}
                      </span>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </Panel>
    </div>
  );
}

function PodiumCard({
  item,
  rank,
  max,
  unit,
  delay,
}: {
  item: RankingItem;
  rank: number;
  max: number;
  unit?: string;
  delay: number;
}) {
  const ratio = (item.value / max) * 100;
  const palette =
    rank === 1
      ? {
          ring: "ring-[#f5b400]/40",
          glow: "from-[#fff7df] to-transparent",
          chip: "bg-[#fef0c7] text-[#9a6b00]",
          number: "text-[#9a6b00]",
        }
      : rank === 2
        ? {
            ring: "ring-[color:var(--border-strong)]",
            glow: "from-[#f1f3f8] to-transparent",
            chip: "bg-[color:var(--surface-2)] text-[color:var(--muted-foreground)]",
            number: "text-[color:var(--foreground)]",
          }
        : {
            ring: "ring-[#cd7f32]/40",
            glow: "from-[#fdeede] to-transparent",
            chip: "bg-[#fdeede] text-[#a86224]",
            number: "text-[#a86224]",
          };

  return (
    <div
      className={cn(
        "ga-card reveal relative overflow-hidden p-5 ring-1",
        palette.ring
      )}
      style={{ ["--d" as string]: `${delay}ms` }}
    >
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-0 bg-gradient-to-br opacity-70",
          palette.glow
        )}
      />
      <div className="relative">
        <div className="flex items-center justify-between">
          <div className={cn("chip", palette.chip)}>
            {rank === 1 && <Crown className="h-3 w-3" />}#{rank}
          </div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.16em] text-[color:var(--muted-foreground)]">
            <ListOrdered className="-mt-0.5 mr-1 inline h-3 w-3" />
            Podium
          </div>
        </div>
        <Link
          href={`/videos/${item.video_id}`}
          className="mt-4 block line-clamp-2 text-[14.5px] font-semibold leading-snug text-[color:var(--foreground)] hover:text-[color:var(--primary)]"
        >
          {item.title}
        </Link>
        <div className="mt-3 flex items-baseline gap-1.5">
          <span
            className={cn(
              "ticker text-[28px] leading-none",
              palette.number
            )}
          >
            {formatCompact(item.value)}
          </span>
          {unit && (
            <span className="text-[11px] font-medium text-[color:var(--muted-foreground)]">
              {unit}
            </span>
          )}
        </div>
        <div className="mt-3 text-[11px] text-[color:var(--muted-foreground)]">
          {formatDate(item.published_at)} 公開 · トップとの比 {ratio.toFixed(0)}
          %
        </div>
        <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-[color:var(--surface-2)]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[color:var(--primary)] to-[color:var(--accent)]"
            style={{ width: `${ratio}%` }}
          />
        </div>
      </div>
    </div>
  );
}
