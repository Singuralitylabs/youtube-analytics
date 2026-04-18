"use client";

import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";

import { BarChart } from "@/components/charts/BarChart";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiPaths, fetcher } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/utils";
import type { MetricKey, RankingItem } from "@/types";

const METRIC_OPTIONS: { value: MetricKey; label: string }[] = [
  { value: "views", label: "再生数 (views)" },
  {
    value: "estimatedMinutesWatched",
    label: "総視聴時間 (estimatedMinutesWatched)",
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

export default function RankingsPage() {
  const [metric, setMetric] = useState<MetricKey>("views");
  const [days, setDays] = useState("30");

  const { data, isLoading, error } = useSWR<RankingItem[]>(
    apiPaths.rankings(metric, 20, Number(days)),
    fetcher
  );

  const chartData = (data ?? []).slice(0, 10).map((r) => ({
    title:
      r.title.length > 30 ? `${r.title.slice(0, 30)}…` : r.title,
    value: r.value,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">動画ランキング</h1>
        <p className="text-sm text-muted-foreground">
          指標・期間を切り替えて上位動画を確認
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>フィルター</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4">
          <div className="min-w-[240px] flex-1">
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
          <div className="min-w-[200px] flex-1">
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
        <CardHeader>
          <CardTitle>Top 10 グラフ</CardTitle>
          <CardDescription>上位10本を横棒グラフで表示</CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <ErrorState />
          ) : chartData.length > 0 ? (
            <BarChart
              data={chartData}
              xKey="title"
              yKey="value"
              layout="vertical"
              height={400}
              yTickFormatter={(v) => formatNumber(v)}
            />
          ) : (
            <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
              {isLoading ? "読み込み中…" : "データがありません"}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>ランキングテーブル</CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <ErrorState />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">#</TableHead>
                  <TableHead>タイトル</TableHead>
                  <TableHead className="w-32">公開日</TableHead>
                  <TableHead className="w-32 text-right">値</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data ?? []).map((r) => (
                  <TableRow key={r.video_id}>
                    <TableCell className="font-medium">{r.rank}</TableCell>
                    <TableCell>
                      <Link
                        href={`/videos/${r.video_id}`}
                        className="underline-offset-4 hover:underline"
                      >
                        {r.title}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(r.published_at)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatNumber(r.value)}
                    </TableCell>
                  </TableRow>
                ))}
                {!isLoading && (data?.length ?? 0) === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={4}
                      className="py-10 text-center text-muted-foreground"
                    >
                      データがありません
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="flex h-[200px] items-center justify-center text-sm text-destructive">
      データの取得に失敗しました
    </div>
  );
}
