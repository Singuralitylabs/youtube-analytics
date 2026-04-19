"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import {
  Activity,
  ArrowUpRight,
  Eye,
  PlayCircle,
  RefreshCw,
  Users,
  Video,
} from "lucide-react";

import { LineChart } from "@/components/charts/LineChart";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/EmptyState";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { api, apiPaths, fetcher } from "@/lib/api";
import {
  formatCompact,
  formatNumber,
  formatShortDate,
  pctDelta,
} from "@/lib/utils";
import type {
  ChannelStats,
  RankingItem,
  TimeseriesPoint,
} from "@/types";

type Range = "7" | "30" | "90";

const RANGE_OPTIONS = [
  { value: "7" as Range, label: "7D" },
  { value: "30" as Range, label: "30D" },
  { value: "90" as Range, label: "90D" },
];

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
  const { data: topVideos } = useSWR<RankingItem[]>(
    apiPaths.rankings("views", 5, 30),
    fetcher
  );

  const [range, setRange] = useState<Range>("30");
  const [collecting, setCollecting] = useState(false);
  const [collectMsg, setCollectMsg] = useState<string | null>(null);
  const [collectKind, setCollectKind] = useState<"ok" | "err" | null>(null);

  async function onCollect() {
    setCollecting(true);
    setCollectMsg(null);
    setCollectKind(null);
    try {
      const r = await api.collect();
      setCollectKind("ok");
      setCollectMsg(
        `収集完了 — 登録者 ${formatNumber(r.subscriber_count)} / 総再生 ${formatNumber(r.total_view_count)}`
      );
    } catch (e) {
      setCollectKind("err");
      setCollectMsg(
        `収集失敗: ${e instanceof Error ? e.message : String(e)}`
      );
    } finally {
      setCollecting(false);
    }
  }

  const days = Number(range);
  const subsTrend = useMemo(
    () => sliceTrend(subsSeries, days),
    [subsSeries, days]
  );
  const viewsTrend = useMemo(
    () => sliceTrend(viewsSeries, days),
    [viewsSeries, days]
  );

  const subsDelta = pctDelta(
    subsTrend.at(-1)?.value,
    subsTrend.at(0)?.value
  );
  const viewsDelta = pctDelta(
    viewsTrend.at(-1)?.value,
    viewsTrend.at(0)?.value
  );

  const subsChartData = subsTrend.map((p) => ({
    date: p.collected_at,
    value: p.value,
  }));
  const viewsChartData = viewsTrend.map((p) => ({
    date: p.collected_at,
    value: p.value,
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Channel Overview"
        title="ダッシュボード"
        description="登録者数と視聴数の推移を中心に、チャンネル全体の傾向を確認します。最新値は YouTube Data API、推移は Google Sheets に蓄積されたスナップショットを使用しています。"
        actions={
          <>
            <SegmentedControl
              value={range}
              onChange={setRange}
              options={RANGE_OPTIONS}
              label="期間"
            />
            <Button onClick={onCollect} disabled={collecting} size="default">
              <RefreshCw className={collecting ? "animate-spin" : undefined} />
              {collecting ? "収集中…" : "データ収集"}
            </Button>
          </>
        }
      />

      {collectMsg && (
        <div
          className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-[12.5px] ${
            collectKind === "ok"
              ? "border-[color:var(--success)]/30 bg-[#e6f4ea] text-[color:var(--success)]"
              : "border-[color:var(--danger)]/30 bg-[#fce8e6] text-[color:var(--danger)]"
          }`}
        >
          <Activity className="h-3.5 w-3.5" />
          <span className="font-medium">{collectMsg}</span>
        </div>
      )}

      {/* KPI strip — only metrics backed by real data */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <KpiCard
          delay={0}
          label="登録者"
          value={statsLoading ? "…" : formatNumber(stats?.subscriber_count)}
          hint={`直近 ${range} 日間の推移`}
          icon={<Users className="h-3.5 w-3.5" />}
          delta={subsDelta}
          trend={subsTrend.map((p) => p.value)}
          trendColor="var(--chart-1)"
          loading={statsLoading}
        />
        <KpiCard
          delay={80}
          label="総再生数"
          value={statsLoading ? "…" : formatCompact(stats?.total_view_count)}
          hint={
            stats
              ? `${formatNumber(stats.total_view_count)} 回（累計）`
              : undefined
          }
          icon={<Eye className="h-3.5 w-3.5" />}
          delta={viewsDelta}
          trend={viewsTrend.map((p) => p.value)}
          trendColor="var(--chart-2)"
          loading={statsLoading}
        />
        <KpiCard
          delay={160}
          label="公開動画"
          value={statsLoading ? "…" : formatNumber(stats?.video_count)}
          hint="チャンネルの全動画数"
          icon={<Video className="h-3.5 w-3.5" />}
          loading={statsLoading}
        />
      </section>

      {/* Main charts */}
      <section className="grid gap-4 xl:grid-cols-3">
        <Panel
          className="xl:col-span-2"
          eyebrow="Subscribers"
          title="登録者数の推移"
          description="Google Sheets に蓄積された日次スナップショット"
          actions={
            <span className="chip bg-[color:var(--primary-soft)] text-[color:var(--primary)]">
              <ArrowUpRight className="h-3 w-3" />
              {subsDelta !== null
                ? `${subsDelta > 0 ? "+" : ""}${subsDelta.toFixed(2)}%`
                : "—"}
            </span>
          }
        >
          {subsChartData.length > 0 ? (
            <LineChart
              data={subsChartData}
              xKey="date"
              series={[
                { key: "value", name: "登録者数", color: "var(--chart-1)" },
              ]}
              yTickFormatter={(v) => formatCompact(v)}
              xTickFormatter={formatShortDate}
              height={320}
            />
          ) : (
            <EmptyState
              title="データがありません"
              message="『データ収集』を実行すると、登録者数のスナップショットが Google Sheets に保存され、ここに表示されます。"
            />
          )}
        </Panel>

        <Panel
          eyebrow="Top videos · 30D"
          title="再生数トップ 5"
          description="直近 30 日間の再生数ランキング"
        >
          <ol className="space-y-2">
            {(topVideos ?? []).slice(0, 5).map((v, i) => (
              <li
                key={v.video_id}
                className="reveal flex items-center gap-3 rounded-lg border border-transparent px-2 py-2 transition-colors hover:border-[color:var(--border)] hover:bg-[color:var(--surface-2)]/50"
                style={{ ["--d" as string]: `${i * 60}ms` }}
              >
                <RankPill rank={v.rank} />
                <div className="min-w-0 flex-1">
                  <a
                    href={`/videos/${v.video_id}`}
                    className="line-clamp-2 text-[12.5px] font-medium leading-tight text-[color:var(--foreground)] hover:text-[color:var(--primary)]"
                  >
                    {v.title}
                  </a>
                  <div className="mt-0.5 flex items-center gap-1.5 text-[10.5px] text-[color:var(--muted-foreground)]">
                    <PlayCircle className="h-3 w-3" />
                    {v.published_at?.split("T")[0] ?? "-"}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <div className="font-num text-[13.5px] text-[color:var(--foreground)]">
                    {formatCompact(v.value)}
                  </div>
                  <div className="text-[9.5px] uppercase tracking-wider text-[color:var(--muted-foreground)]">
                    views
                  </div>
                </div>
              </li>
            ))}
            {(topVideos ?? []).length === 0 && (
              <EmptyState
                message="ランキングデータがまだ取得できていません。"
                height={140}
              />
            )}
          </ol>
        </Panel>
      </section>

      <Panel
        eyebrow="Lifetime views"
        title="総再生数の推移"
        description="累積視聴回数の推移を確認"
      >
        {viewsChartData.length > 0 ? (
          <LineChart
            data={viewsChartData}
            xKey="date"
            series={[
              { key: "value", name: "総再生数", color: "var(--chart-2)" },
            ]}
            yTickFormatter={(v) => formatCompact(v)}
            xTickFormatter={formatShortDate}
            height={260}
          />
        ) : (
          <EmptyState message="データがありません。データ収集後にこの図が描画されます。" />
        )}
      </Panel>
    </div>
  );
}

function RankPill({ rank }: { rank: number }) {
  const palette =
    rank === 1
      ? "from-[#f5b400] to-[#f29900] text-white"
      : rank === 2
        ? "from-[#9aa0a6] to-[#5f6368] text-white"
        : rank === 3
          ? "from-[#cd7f32] to-[#a86224] text-white"
          : "from-[color:var(--surface-2)] to-[color:var(--surface-2)] text-[color:var(--muted-foreground)] ring-1 ring-[color:var(--border-strong)]";
  return (
    <div
      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br font-num text-[12px] font-semibold ${palette}`}
    >
      {rank}
    </div>
  );
}

function sliceTrend(
  series: TimeseriesPoint[] | undefined,
  days: number
): TimeseriesPoint[] {
  if (!series || series.length === 0) return [];
  const sorted = [...series].sort((a, b) =>
    a.collected_at.localeCompare(b.collected_at)
  );
  if (sorted.length <= days) return sorted;
  return sorted.slice(-days);
}
