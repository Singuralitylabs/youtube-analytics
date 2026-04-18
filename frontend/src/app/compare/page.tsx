"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { Check } from "lucide-react";

import { LineChart } from "@/components/charts/LineChart";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn, formatNumber } from "@/lib/utils";
import { apiPaths, fetcher } from "@/lib/api";
import type { CompareItem, MetricKey, VideoSummary } from "@/types";

const METRIC_OPTIONS: { value: MetricKey; label: string }[] = [
  { value: "views", label: "再生数 (views)" },
  {
    value: "estimatedMinutesWatched",
    label: "総視聴時間 (estimatedMinutesWatched)",
  },
  {
    value: "averageViewDuration",
    label: "平均視聴時間 (averageViewDuration)",
  },
  {
    value: "averageViewPercentage",
    label: "平均視聴維持率 (averageViewPercentage)",
  },
];

const DAYS_OPTIONS = [
  { value: "7", label: "直近7日" },
  { value: "30", label: "直近30日" },
  { value: "60", label: "直近60日" },
  { value: "90", label: "直近90日" },
];

const COLORS = [
  "#2563eb",
  "#dc2626",
  "#16a34a",
  "#ca8a04",
  "#9333ea",
  "#0891b2",
  "#db2777",
  "#ea580c",
];

export default function ComparePage() {
  const { data: videos } = useSWR<VideoSummary[]>(
    apiPaths.videos(),
    fetcher
  );

  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [metric, setMetric] = useState<MetricKey>("views");
  const [days, setDays] = useState("30");

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

  const { data: compareData } = useSWR<CompareItem[]>(
    selected.length > 0
      ? apiPaths.compare(selected, metric, Number(days))
      : null,
    fetcher
  );

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

  const series = useMemo(() => {
    if (!compareData) return [];
    const titleByVideoId = new Map<string, string>();
    for (const row of compareData) {
      titleByVideoId.set(row.video_id, row.title);
    }
    return selected.map((id, i) => ({
      key: id,
      name: titleByVideoId.get(id) ?? id,
      color: COLORS[i % COLORS.length],
    }));
  }, [compareData, selected]);

  function toggle(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">比較分析</h1>
        <p className="text-sm text-muted-foreground">
          複数動画の指標を重ねて比較
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>フィルター</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              指標
            </label>
            <Select
              value={metric}
              onValueChange={(v) => setMetric(v as MetricKey)}
            >
              <SelectTrigger>
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
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">
              期間
            </label>
            <Select value={days} onValueChange={setDays}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DAYS_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>動画を選択</CardTitle>
            <CardDescription>
              {selected.length} 本選択中
            </CardDescription>
          </div>
          {selected.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelected([])}
            >
              選択解除
            </Button>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder="タイトルまたは動画IDで絞り込み"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="max-h-72 overflow-y-auto rounded-md border">
            {filteredVideos.length === 0 ? (
              <div className="p-4 text-sm text-muted-foreground">
                {videos === undefined
                  ? "読み込み中…"
                  : "該当する動画がありません"}
              </div>
            ) : (
              <ul className="divide-y">
                {filteredVideos.map((v) => {
                  const isSelected = selected.includes(v.video_id);
                  return (
                    <li key={v.video_id}>
                      <button
                        type="button"
                        onClick={() => toggle(v.video_id)}
                        className={cn(
                          "flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-accent",
                          isSelected && "bg-accent"
                        )}
                      >
                        <span
                          className={cn(
                            "flex h-5 w-5 items-center justify-center rounded border",
                            isSelected
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-input"
                          )}
                        >
                          {isSelected && <Check className="h-3 w-3" />}
                        </span>
                        <span className="flex-1 truncate">{v.title}</span>
                        <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                          {formatNumber(v.view_count)} views
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>比較グラフ</CardTitle>
          <CardDescription>選択動画の時系列を重ねて表示</CardDescription>
        </CardHeader>
        <CardContent>
          {selected.length === 0 ? (
            <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
              動画を選択してください
            </div>
          ) : chartData.length > 0 ? (
            <LineChart
              data={chartData}
              xKey="date"
              series={series}
              height={400}
              yTickFormatter={(v) => formatNumber(v)}
            />
          ) : (
            <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
              データ取得中…
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
