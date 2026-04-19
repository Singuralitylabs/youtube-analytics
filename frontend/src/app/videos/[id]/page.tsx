"use client";

import Link from "next/link";
import { use, useState } from "react";
import useSWR from "swr";
import {
  ArrowLeft,
  Eye,
  ExternalLink,
  MessageCircle,
  PlayCircle,
  ThumbsUp,
  Timer,
} from "lucide-react";

import { BarChart } from "@/components/charts/BarChart";
import { LineChart } from "@/components/charts/LineChart";
import { PieChart } from "@/components/charts/PieChart";
import { EmptyState } from "@/components/ui/EmptyState";
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
  formatDate,
  formatDuration,
  formatNumber,
  formatShortDate,
} from "@/lib/utils";
import type {
  Demographic,
  MetricKey,
  TrafficSource,
  VideoDetail,
  VideoTimeseriesPoint,
} from "@/types";

type Days = "7" | "30" | "60" | "90";

const METRIC_OPTIONS: { value: MetricKey; label: string; unit?: string }[] = [
  { value: "views", label: "再生数", unit: "回" },
  {
    value: "estimatedMinutesWatched",
    label: "総視聴時間",
    unit: "分",
  },
  {
    value: "averageViewDuration",
    label: "平均視聴時間",
    unit: "秒",
  },
  {
    value: "averageViewPercentage",
    label: "平均視聴維持率",
    unit: "%",
  },
];

const DAYS_OPTIONS: { value: Days; label: string }[] = [
  { value: "7", label: "7D" },
  { value: "30", label: "30D" },
  { value: "60", label: "60D" },
  { value: "90", label: "90D" },
];

export default function VideoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [metric, setMetric] = useState<MetricKey>("views");
  const [days, setDays] = useState<Days>("30");
  const metricMeta = METRIC_OPTIONS.find((m) => m.value === metric);

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

  const trafficPie = (traffic ?? [])
    .sort((a, b) => b.views - a.views)
    .map((t) => ({
      name: prettyTrafficLabel(t.traffic_source_type),
      value: t.views,
    }));

  const demoChart = (demographics ?? []).map((d) => ({
    group: `${d.age_group} ${d.gender === "male" ? "♂" : d.gender === "female" ? "♀" : d.gender}`,
    value: d.view_percentage,
  }));

  const totalSeries = (timeseries ?? []).reduce(
    (s, p) => s + (p.value || 0),
    0
  );
  const peakDay = (timeseries ?? []).reduce<VideoTimeseriesPoint | null>(
    (max, p) => (max === null || p.value > max.value ? p : max),
    null
  );

  return (
    <div className="space-y-6">
      {/* Hero header */}
      <Link
        href="/rankings"
        className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        ランキングへ戻る
      </Link>

      <div className="ga-card relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-br from-[color:var(--primary-soft)] via-transparent to-transparent opacity-80"
        />
        <div className="relative flex flex-col gap-5 p-6 lg:flex-row lg:items-center">
          <div className="flex h-24 w-40 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-[#1a73e8] via-[#5e7ce0] to-[#0b8d77] text-white shadow-[0_10px_30px_-10px_rgba(26,115,232,0.55)]">
            <PlayCircle className="h-10 w-10 drop-shadow" strokeWidth={1.5} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2 text-[10.5px] font-semibold uppercase tracking-[0.16em] text-[color:var(--muted-foreground)]">
              <span>Video · ID</span>
              <code className="font-num rounded bg-[color:var(--surface-2)] px-1.5 py-0.5 text-[10.5px] tracking-normal text-[color:var(--foreground)]">
                {id}
              </code>
            </div>
            <h1 className="mt-2 font-display text-[26px] leading-tight text-[color:var(--foreground)]">
              {detailLoading
                ? "読み込み中…"
                : detail?.title ?? "(タイトル不明)"}
            </h1>
            {detail && (
              <p className="mt-1.5 text-[13px] text-[color:var(--muted-foreground)]">
                {formatDate(detail.published_at)} 公開 ・ 長さ{" "}
                {formatDuration(detail.duration_sec)}
              </p>
            )}
          </div>
          <a
            href={`https://www.youtube.com/watch?v=${id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-[color:var(--border-strong)] bg-[color:var(--surface)] px-3.5 py-2 text-[12.5px] font-semibold text-[color:var(--foreground)] hover:bg-[color:var(--surface-2)]"
          >
            YouTube で開く
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>

        {/* Stats strip embedded in hero */}
        <div className="hairline" />
        <dl className="grid grid-cols-2 divide-y divide-[color:var(--border)] sm:grid-cols-4 sm:divide-y-0 sm:divide-x">
          <Stat icon={<Eye className="h-3.5 w-3.5" />} label="再生数" value={formatNumber(detail?.view_count)} />
          <Stat icon={<ThumbsUp className="h-3.5 w-3.5" />} label="高評価" value={formatNumber(detail?.like_count)} />
          <Stat icon={<MessageCircle className="h-3.5 w-3.5" />} label="コメント" value={formatNumber(detail?.comment_count)} />
          <Stat icon={<Timer className="h-3.5 w-3.5" />} label="長さ" value={detail ? formatDuration(detail.duration_sec) : "-"} />
        </dl>
      </div>

      {/* Time-series panel */}
      <Panel
        eyebrow="Daily timeseries"
        title="指標の推移"
        description={`YouTube Analytics API ・ 直近 ${days} 日間`}
        actions={
          <div className="flex items-center gap-2">
            <SegmentedControl
              value={days}
              onChange={setDays}
              options={DAYS_OPTIONS}
              label="期間"
              size="sm"
            />
            <div className="min-w-[180px]">
              <Select
                value={metric}
                onValueChange={(v) => setMetric(v as MetricKey)}
              >
                <SelectTrigger className="h-8 text-[12px]">
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
          </div>
        }
      >
        {(timeseries?.length ?? 0) > 0 ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-6 text-[12px] text-[color:var(--muted-foreground)]">
              <MiniStat
                label="期間合計"
                value={`${formatNumber(totalSeries)} ${metricMeta?.unit ?? ""}`}
              />
              {peakDay && (
                <MiniStat
                  label="最大日"
                  value={`${formatShortDate(peakDay.date)} ・ ${formatNumber(peakDay.value)}`}
                />
              )}
              <MiniStat
                label="計測日数"
                value={`${timeseries?.length ?? 0} 日`}
              />
            </div>
            <LineChart
              data={
                (timeseries ?? []) as unknown as Record<string, unknown>[]
              }
              xKey="date"
              series={[
                {
                  key: "value",
                  name: metricMeta?.label ?? metric,
                  color: "var(--chart-1)",
                },
              ]}
              yTickFormatter={(v) => formatCompact(v)}
              xTickFormatter={formatShortDate}
              height={300}
            />
          </div>
        ) : (
          <EmptyState message="この期間に十分なデータがありません。指標または期間を変更してください。" />
        )}
      </Panel>

      {/* Two-up: Traffic + Demographics */}
      <section className="grid gap-4 xl:grid-cols-2">
        <Panel
          eyebrow="Traffic sources"
          title="流入経路"
          description={`再生のきっかけ ・ 直近 ${days} 日`}
        >
          {trafficPie.length > 0 ? (
            <PieChart data={trafficPie} height={260} />
          ) : (
            <EmptyState message="流入経路データがありません" />
          )}
        </Panel>

        <Panel
          eyebrow="Demographics"
          title="視聴者属性"
          description="年齢 × 性別ごとの視聴シェア"
        >
          {demoChart.length > 0 ? (
            <BarChart
              data={demoChart}
              xKey="group"
              yKey="value"
              color="var(--chart-5)"
              yTickFormatter={(v) => `${v}%`}
              height={260}
              rainbow
            />
          ) : (
            <EmptyState message="属性データがありません" />
          )}
        </Panel>
      </section>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className={cn("p-5")}>
      <div className="flex items-center gap-1.5 text-[10.5px] font-semibold uppercase tracking-[0.14em] text-[color:var(--muted-foreground)]">
        {icon}
        {label}
      </div>
      <div className="ticker mt-1.5 text-[22px] text-[color:var(--foreground)]">
        {value}
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--muted-foreground)]">
        {label}
      </div>
      <div className="font-num mt-0.5 text-[14px] text-[color:var(--foreground)]">
        {value}
      </div>
    </div>
  );
}

function prettyTrafficLabel(s: string): string {
  // Best-effort label formatting for known traffic source codes
  const map: Record<string, string> = {
    YT_SEARCH: "YouTube 検索",
    YT_CHANNEL: "チャンネルページ",
    YT_OTHER_PAGE: "他のYTページ",
    SUBSCRIBER: "登録フィード",
    EXT_URL: "外部リンク",
    NO_LINK_OTHER: "直リンクなし",
    NO_LINK_EMBEDDED: "外部埋め込み",
    PLAYLIST: "プレイリスト",
    NOTIFICATION: "通知",
    ADVERTISING: "広告",
    RELATED_VIDEO: "関連動画",
    SHORTS: "Shorts",
    HASHTAGS: "ハッシュタグ",
    BROWSE: "ホーム/急上昇",
  };
  return map[s] ?? s;
}
