export type MetricKey =
  | "views"
  | "estimatedMinutesWatched"
  | "averageViewDuration"
  | "averageViewPercentage";

export type ChannelTimeseriesMetric = "subscriber_count" | "total_view_count";

export interface ChannelStats {
  channel_id: string;
  subscriber_count: number;
  total_view_count: number;
  video_count: number;
}

export interface TimeseriesPoint {
  collected_at: string;
  value: number;
}

export interface VideoSummary {
  video_id: string;
  title: string;
  published_at: string;
  view_count: number;
  like_count: number;
  comment_count: number;
}

export interface VideoDetail {
  video_id: string;
  title: string;
  published_at: string;
  duration_sec: number;
  view_count: number;
  like_count: number;
  comment_count: number;
}

export interface VideoTimeseriesPoint {
  date: string;
  value: number;
}

export interface TrafficSource {
  traffic_source_type: string;
  views: number;
}

export interface Demographic {
  age_group: string;
  gender: string;
  view_percentage: number;
}

export interface RankingItem {
  rank: number;
  video_id: string;
  title: string;
  published_at: string;
  value: number;
}

export interface CompareItem {
  video_id: string;
  title: string;
  date: string;
  value: number;
}

export interface CollectResult {
  status: string;
  collected_at: string;
  subscriber_count: number;
  total_view_count: number;
}
