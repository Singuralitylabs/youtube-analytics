"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { Check, GitCompareArrows, Search, X } from "lucide-react";

import { LineChart } from "@/components/charts/LineChart";
import { CHART_COLORS } from "@/components/charts/shared";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiPaths, fetcher } from "@/lib/api";
import {
  cn,
  formatCompact,
  formatNumber,
  formatShortDate,
} from "@/lib/utils";
import type { CompareItem, MetricKey, VideoSummary } from "@/types";

type Days = "7" | "30" | "60" | "90";

const METRIC_OPTIONS: { value: MetricKey; label: string }[] = [
  { value: "views", label: "再生数" },
  { value: "estimatedMinutesWatched", label: "総視聴時間" },
  { value: "averageViewDuration", label: "平均視聴時間" },
  { value: "averageViewPercentage", label: "平均視聴維持率" },
];

const DAYS_OPTIONS: { value: Days; label: string }[] = [
  { value: "7", label: "7D" },
  { value: "30", label: "30D" },
  { value: "60", label: "60D" },
  { value: "90", label: "90D" },
];

const MAX_COMPARE = 8;

export default function ComparePage() {
  const { data: videos } = useSWR<VideoSummary[]>(
    apiPaths.videos(),
    fetcher
  );

  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [metric, setMetric] = useState<MetricKey>("views");
  const [days, setDays] = useState<Days>("30");

  const filteredVideos = useMemo(() => {
    const list = videos ?? [];
    if (!filter) return list;
    const q = filter.toLowerCase();
    return list.filter(
      (v) =>
        v.title.toLowerCase().includes(q) ||
        v.video_id.toLowerCase().includes(q)
    );
  }, [videos, filter]);

  const { data: compareData, isLoading: comparing } = useSWR<CompareItem[]>(
    selected.length > 0
      ? apiPaths.compare(selected, metric, Number(days))
      : null,
    fetcher
  );

  const titleByVideoId = useMemo(() => {
    const m = new Map<string, string>();
    for (const v of videos ?? []) m.set(v.video_id, v.title);
    return m;
  }, [videos]);

  const chartData = useMemo(() => {
    if (!compareData || compareData.length === 0) return [];
    const byDate = new Map<string, Record<string, unknown>>();
    for (const row of compareData) {
      const bucket = byDate.get(row.date) ?? { date: row.date };
      bucket[row.video_id] = row.value;
      byDate.set(row.date, bucket);
    }
    return Array.from(byDate.values()).sort((a, b) =>
      String(a.date).localeCompare(String(b.date))
    );
  }, [compareData]);

  const series = useMemo(
    () =>
      selected.map((id, i) => ({
        key: id,
        name: titleByVideoId.get(id) ?? id,
        color: CHART_COLORS[i % CHART_COLORS.length],
      })),
    [selected, titleByVideoId]
  );

  const totals = useMemo(() => {
    const map = new Map<string, number>();
    for (const row of compareData ?? []) {
      map.set(row.video_id, (map.get(row.video_id) ?? 0) + row.value);
    }
    return map;
  }, [compareData]);

  function toggle(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_COMPARE) return prev;
      return [...prev, id];
    });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Side-by-side"
        title="比較分析"
        description={`動画を最大 ${MAX_COMPARE} 本まで重ねて、指標の差を視覚的に比較します。`}
        actions={
          <SegmentedControl
            value={days}
            onChange={setDays}
            options={DAYS_OPTIONS}
            label="期間"
          />
        }
      />

      {/* Selection chips bar */}
      <div className="ga-card flex flex-wrap items-center gap-2 px-4 py-3">
        <div className="flex items-center gap-2 text-[11.5px] font-semibold uppercase tracking-[0.14em] text-[color:var(--muted-foreground)]">
          <GitCompareArrows className="h-3.5 w-3.5" />
          選択中
          <span className="font-num text-[12.5px] text-[color:var(--foreground)]">
            {selected.length}/{MAX_COMPARE}
          </span>
        </div>
        <div className="flex flex-1 flex-wrap gap-1.5">
          {selected.length === 0 && (
            <span className="text-[12px] text-[color:var(--muted-foreground)]">
              下のリストから動画を選んでください
            </span>
          )}
          {selected.map((id, i) => {
            const color = CHART_COLORS[i % CHART_COLORS.length];
            return (
              <button
                key={id}
                onClick={() => toggle(id)}
                className="group inline-flex max-w-[260px] items-center gap-1.5 rounded-full border border-[color:var(--border)] bg-[color:var(--surface)] py-1 pl-1.5 pr-2 text-[11.5px] font-medium hover:border-[color:var(--border-strong)]"
              >
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{ background: color }}
                />
                <span className="line-clamp-1">
                  {titleByVideoId.get(id) ?? id}
                </span>
                <X className="h-3 w-3 text-[color:var(--muted-foreground)] group-hover:text-[color:var(--danger)]" />
              </button>
            );
          })}
        </div>
        {selected.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => setSelected([])}>
            すべて解除
          </Button>
        )}
      </div>

      {/* Metric switcher */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[color:var(--muted-foreground)]">
          指標
        </span>
        <Select
          value={metric}
          onValueChange={(v) => setMetric(v as MetricKey)}
        >
          <SelectTrigger className="w-[260px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {METRIC_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
        {/* Picker */}
        <Panel
          eyebrow="Library"
          title="動画ピッカー"
          description={`${filteredVideos.length} 件 / ${videos?.length ?? 0} 件`}
          bodyPadding={false}
          className="xl:max-h-[640px]"
        >
          <div className="border-b border-[color:var(--border)] p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--muted-foreground)]" />
              <Input
                placeholder="タイトル / ID で絞り込み"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
          <div className="max-h-[520px] overflow-y-auto">
            {filteredVideos.length === 0 ? (
              <div className="p-4">
                <EmptyState
                  message={
                    videos === undefined
                      ? "読み込み中…"
                      : "該当する動画がありません"
                  }
                  height={140}
                />
              </div>
            ) : (
              <ul className="divide-y divide-[color:var(--border)]">
                {filteredVideos.map((v) => {
                  const isSelected = selected.includes(v.video_id);
                  const idx = selected.indexOf(v.video_id);
                  const color =
                    idx >= 0 ? CHART_COLORS[idx % CHART_COLORS.length] : null;
                  const disabled =
                    !isSelected && selected.length >= MAX_COMPARE;
                  return (
                    <li key={v.video_id}>
                      <button
                        type="button"
                        onClick={() => toggle(v.video_id)}
                        disabled={disabled}
                        className={cn(
                          "flex w-full items-start gap-3 px-3.5 py-2.5 text-left transition-colors",
                          isSelected
                            ? "bg-[color:var(--primary-soft)]/40"
                            : "hover:bg-[color:var(--surface-2)]/60",
                          disabled && "cursor-not-allowed opacity-40"
                        )}
                      >
                        <span
                          className={cn(
                            "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-[5px] border transition-all",
                            isSelected
                              ? "border-transparent text-white"
                              : "border-[color:var(--border-strong)] bg-[color:var(--surface)]"
                          )}
                          style={
                            isSelected && color
                              ? { backgroundColor: color }
                              : undefined
                          }
                        >
                          {isSelected && <Check className="h-2.5 w-2.5" />}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="line-clamp-2 text-[12.5px] font-medium leading-snug text-[color:var(--foreground)]">
                            {v.title}
                          </div>
                          <div className="mt-1 flex items-center gap-2 text-[10.5px] text-[color:var(--muted-foreground)]">
                            <span className="font-num">
                              {formatCompact(v.view_count)} views
                            </span>
                            <span className="opacity-50">·</span>
                            <span>
                              {v.published_at?.split("T")[0] ?? "-"}
                            </span>
                          </div>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Panel>

        {/* Chart + leaderboard */}
        <div className="space-y-4">
          <Panel
            eyebrow="Overlay"
            title="比較グラフ"
            description="選択した動画の時系列を重ねて表示"
          >
            {selected.length === 0 ? (
              <EmptyState
                title="動画を選択してください"
                message="左の動画ピッカーから 2 本以上を選ぶと、ここに重ねて描画されます。"
                height={300}
              />
            ) : comparing ? (
              <div className="space-y-2">
                <div className="skeleton h-8 w-1/3" />
                <div className="skeleton h-[280px] w-full" />
              </div>
            ) : chartData.length > 0 ? (
              <LineChart
                data={chartData}
                xKey="date"
                series={series}
                height={340}
                yTickFormatter={(v) => formatCompact(v)}
                xTickFormatter={formatShortDate}
                area={false}
              />
            ) : (
              <EmptyState message="期間内のデータがありません" />
            )}
          </Panel>

          {selected.length > 0 && (
            <Panel
              eyebrow="Sums"
              title="期間内合計"
              description={`${METRIC_OPTIONS.find((m) => m.value === metric)?.label} ・ 直近 ${days} 日`}
              bodyPadding={false}
            >
              <ul className="divide-y divide-[color:var(--border)]">
                {selected.map((id, i) => {
                  const color = CHART_COLORS[i % CHART_COLORS.length];
                  const total = totals.get(id) ?? 0;
                  const max = Math.max(...Array.from(totals.values()), 1);
                  const pct = (total / max) * 100;
                  return (
                    <li
                      key={id}
                      className="flex items-center gap-3 px-5 py-3"
                    >
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-sm"
                        style={{ background: color }}
                      />
                      <Link
                        href={`/videos/${id}`}
                        className="line-clamp-1 flex-1 text-[12.5px] font-medium text-[color:var(--foreground)] hover:text-[color:var(--primary)]"
                      >
                        {titleByVideoId.get(id) ?? id}
                      </Link>
                      <div className="hidden h-1.5 w-32 overflow-hidden rounded-full bg-[color:var(--surface-2)] md:block">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${pct}%`,
                            background: color,
                          }}
                        />
                      </div>
                      <span className="font-num w-24 text-right text-[13px] text-[color:var(--foreground)]">
                        {formatNumber(total)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </Panel>
          )}
        </div>
      </section>
    </div>
  );
}
