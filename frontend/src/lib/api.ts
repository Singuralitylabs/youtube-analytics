import type {
  ChannelStats,
  ChannelTimeseriesMetric,
  CollectResult,
  CompareItem,
  Demographic,
  MetricKey,
  RankingItem,
  TimeseriesPoint,
  TrafficSource,
  VideoDetail,
  VideoSummary,
  VideoTimeseriesPoint,
} from "@/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail?: string;
  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : undefined;
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiError(res.status, `Request failed: ${res.status}`, detail);
  }
  return (await res.json()) as T;
}

// SWR 用の汎用 fetcher。key = API パス文字列。
export const fetcher = <T>(path: string) => request<T>(path);

function qs(params: Record<string, string | number | undefined | null>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== ""
  );
  if (entries.length === 0) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of entries) sp.append(k, String(v));
  return `?${sp.toString()}`;
}

// ---------- SWR key builders (URL文字列をSWRキーにする) ----------

export const apiPaths = {
  channelStats: () => "/api/channel/stats",
  channelTimeseries: (metric: ChannelTimeseriesMetric = "subscriber_count") =>
    `/api/channel/timeseries${qs({ metric })}`,
  videos: () => "/api/videos",
  video: (id: string) => `/api/videos/${encodeURIComponent(id)}`,
  videoTimeseries: (id: string, metric: MetricKey = "views", days = 30) =>
    `/api/videos/${encodeURIComponent(id)}/timeseries${qs({ metric, days })}`,
  videoTraffic: (id: string, days = 30) =>
    `/api/videos/${encodeURIComponent(id)}/traffic${qs({ days })}`,
  videoDemographics: (id: string, days = 30) =>
    `/api/videos/${encodeURIComponent(id)}/demographics${qs({ days })}`,
  rankings: (metric: MetricKey = "views", limit = 20, days = 30) =>
    `/api/rankings${qs({ metric, limit, days })}`,
  compare: (ids: string[], metric: MetricKey = "views", days = 30) =>
    `/api/compare${qs({ ids: ids.join(","), metric, days })}`,
} as const;

// ---------- 直接呼び出し用クライアント ----------

export const api = {
  channelStats: () => request<ChannelStats>(apiPaths.channelStats()),
  channelTimeseries: (metric?: ChannelTimeseriesMetric) =>
    request<TimeseriesPoint[]>(apiPaths.channelTimeseries(metric)),
  videos: () => request<VideoSummary[]>(apiPaths.videos()),
  video: (id: string) => request<VideoDetail>(apiPaths.video(id)),
  videoTimeseries: (id: string, metric?: MetricKey, days?: number) =>
    request<VideoTimeseriesPoint[]>(apiPaths.videoTimeseries(id, metric, days)),
  videoTraffic: (id: string, days?: number) =>
    request<TrafficSource[]>(apiPaths.videoTraffic(id, days)),
  videoDemographics: (id: string, days?: number) =>
    request<Demographic[]>(apiPaths.videoDemographics(id, days)),
  rankings: (metric?: MetricKey, limit?: number, days?: number) =>
    request<RankingItem[]>(apiPaths.rankings(metric, limit, days)),
  compare: (ids: string[], metric?: MetricKey, days?: number) =>
    request<CompareItem[]>(apiPaths.compare(ids, metric, days)),
  collect: () =>
    request<CollectResult>("/api/collect", { method: "POST" }),
};
