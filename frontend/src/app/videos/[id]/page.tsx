"use client";

import { use, useState } from "react";
import useSWR from "swr";
import {
  Eye,
  MessageCircle,
  ThumbsUp,
  Timer,
} from "lucide-react";

import { BarChart } from "@/components/charts/BarChart";
import { LineChart } from "@/components/charts/LineChart";
import { PieChart } from "@/components/charts/PieChart";
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
import { apiPaths, fetcher } from "@/lib/api";
import { formatDate, formatDuration, formatNumber } from "@/lib/utils";
import type {
  Demographic,
  MetricKey,
  TrafficSource,
  VideoDetail,
  VideoTimeseriesPoint,
} from "@/types";

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

export default function VideoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [metric, setMetric] = useState<MetricKey>("views");
  const [days, setDays] = useState("30");

  const { data: detail, isLoading: detailLoading } = useSWR<VideoDetail>(
    apiPaths.video(id),
    fetcher
  );
  const { data: timeseries } = useSWR<VideoTimeseriesPoint[]>(
    apiPaths.videoTimeseries(id, metric, Number(days)),
    fetcher
  );
  const { data: traffic } = useSWR<TrafficSource[]>(
    apiPaths.videoTraffic(id, Number(days)),
    fetcher
  );
  const { data: demographics } = useSWR<Demographic[]>(
    apiPaths.videoDemographics(id, Number(days)),
    fetcher
  );

  const trafficPie = (traffic ?? []).map((t) => ({
    name: t.traffic_source_type,
    value: t.views,
  }));

  const demoChart = (demographics ?? []).map((d) => ({
    group: `${d.age_group} ${d.gender}`,
    value: d.view_percentage,
  }));

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs text-muted-foreground">
          video_id: <span className="font-mono">{id}</span>
        </p>
        <h1 className="mt-1 text-2xl font-semibold">
          {detailLoading ? "読み込み中…" : detail?.title ?? "(タイトル不明)"}
        </h1>
        {detail && (
          <p className="text-sm text-muted-foreground">
            公開日: {formatDate(detail.published_at)}
          </p>
        )}
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="再生数"
          value={detail?.view_count}
          icon={<Eye className="h-4 w-4 text-muted-foreground" />}
        />
        <MetricCard
          label="高評価"
          value={detail?.like_count}
          icon={<ThumbsUp className="h-4 w-4 text-muted-foreground" />}
        />
        <MetricCard
          label="コメント"
          value={detail?.comment_count}
          icon={<MessageCircle className="h-4 w-4 text-muted-foreground" />}
        />
        <MetricCard
          label="動画の長さ"
          value={
            detail?.duration_sec !== undefined
              ? formatDuration(detail.duration_sec)
              : undefined
          }
          icon={<Timer className="h-4 w-4 text-muted-foreground" />}
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>指標の時系列</CardTitle>
          <CardDescription>日別推移（YouTube Analytics API）</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div className="min-w-[240px]">
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
            <div className="min-w-[160px]">
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
          </div>
          {(timeseries?.length ?? 0) > 0 ? (
            <LineChart
              data={timeseries ?? []}
              xKey="date"
              series={[{ key: "value", name: metric, color: "#2563eb" }]}
              yTickFormatter={(v) => formatNumber(v)}
            />
          ) : (
            <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
              データがありません
            </div>
          )}
        </CardContent>
      </Card>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>流入経路</CardTitle>
            <CardDescription>直近 {days} 日</CardDescription>
          </CardHeader>
          <CardContent>
            {trafficPie.length > 0 ? (
              <PieChart data={trafficPie} />
            ) : (
              <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
                データがありません
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>視聴者属性</CardTitle>
            <CardDescription>年齢 × 性別 (%)</CardDescription>
          </CardHeader>
          <CardContent>
            {demoChart.length > 0 ? (
              <BarChart
                data={demoChart}
                xKey="group"
                yKey="value"
                color="#9333ea"
                yTickFormatter={(v) => `${v}%`}
              />
            ) : (
              <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
                データがありません
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number | string | undefined;
  icon?: React.ReactNode;
}) {
  const display =
    typeof value === "string"
      ? value
      : value === undefined
        ? "…"
        : formatNumber(value);
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tabular-nums">{display}</div>
      </CardContent>
    </Card>
  );
}
