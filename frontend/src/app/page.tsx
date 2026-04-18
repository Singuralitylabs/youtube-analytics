"use client";

import { useState } from "react";
import useSWR from "swr";
import { Eye, RefreshCw, Users, Video } from "lucide-react";

import { BarChart } from "@/components/charts/BarChart";
import { LineChart } from "@/components/charts/LineChart";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, apiPaths, fetcher } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { ChannelStats, TimeseriesPoint } from "@/types";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useSWR<ChannelStats>(
    apiPaths.channelStats(),
    fetcher
  );
  const { data: subsSeries } = useSWR<TimeseriesPoint[]>(
    apiPaths.channelTimeseries("subscriber_count"),
    fetcher
  );
  const { data: viewsSeries } = useSWR<TimeseriesPoint[]>(
    apiPaths.channelTimeseries("total_view_count"),
    fetcher
  );

  const [collecting, setCollecting] = useState(false);
  const [collectMsg, setCollectMsg] = useState<string | null>(null);

  async function onCollect() {
    setCollecting(true);
    setCollectMsg(null);
    try {
      const r = await api.collect();
      setCollectMsg(
        `収集完了: 登録者 ${formatNumber(r.subscriber_count)} 人 / 総再生 ${formatNumber(r.total_view_count)} 回 (${r.collected_at})`
      );
    } catch (e) {
      setCollectMsg(
        `収集失敗: ${e instanceof Error ? e.message : String(e)}`
      );
    } finally {
      setCollecting(false);
    }
  }

  const subsChartData = (subsSeries ?? []).map((p) => ({
    date: p.collected_at,
    value: p.value,
  }));
  const viewsChartData = (viewsSeries ?? []).map((p) => ({
    date: p.collected_at,
    value: p.value,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">ダッシュボード</h1>
          <p className="text-sm text-muted-foreground">
            チャンネル全体のパフォーマンスサマリー
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Button onClick={onCollect} disabled={collecting}>
            <RefreshCw
              className={collecting ? "animate-spin" : undefined}
            />
            {collecting ? "収集中…" : "データ収集"}
          </Button>
          {collectMsg && (
            <p className="text-xs text-muted-foreground">{collectMsg}</p>
          )}
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          label="登録者数"
          value={stats?.subscriber_count}
          loading={statsLoading}
          icon={<Users className="h-4 w-4 text-muted-foreground" />}
        />
        <KpiCard
          label="総再生数"
          value={stats?.total_view_count}
          loading={statsLoading}
          icon={<Eye className="h-4 w-4 text-muted-foreground" />}
        />
        <KpiCard
          label="動画数"
          value={stats?.video_count}
          loading={statsLoading}
          icon={<Video className="h-4 w-4 text-muted-foreground" />}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>登録者数の推移</CardTitle>
            <CardDescription>Google Sheets 記録ベース</CardDescription>
          </CardHeader>
          <CardContent>
            {subsChartData.length > 0 ? (
              <LineChart
                data={subsChartData}
                xKey="date"
                series={[{ key: "value", name: "登録者数", color: "#2563eb" }]}
                yTickFormatter={(v) => formatNumber(v)}
              />
            ) : (
              <EmptyState message="データがありません。『データ収集』ボタンから記録してください。" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>総再生数の推移</CardTitle>
            <CardDescription>Google Sheets 記録ベース</CardDescription>
          </CardHeader>
          <CardContent>
            {viewsChartData.length > 0 ? (
              <BarChart
                data={viewsChartData}
                xKey="date"
                yKey="value"
                color="#16a34a"
                yTickFormatter={(v) => formatNumber(v)}
              />
            ) : (
              <EmptyState message="データがありません。" />
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function KpiCard({
  label,
  value,
  loading,
  icon,
}: {
  label: string;
  value: number | undefined;
  loading: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold tabular-nums">
          {loading ? "…" : formatNumber(value)}
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
      {message}
    </div>
  );
}
