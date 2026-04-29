import client from "./client";

export interface MusicGenerateParams {
  prompt: string;
  model?: string;
  lyrics?: string;
  is_instrumental?: boolean;
  lyrics_optimizer?: boolean;
  output_format?: "url" | "hex";
  aigc_watermark?: boolean;
  audio_url?: string;
  audio_setting?: {
    sample_rate?: number;
    bitrate?: number;
    format?: string;
  };
  variant?: string;
  theme?: string;
}

export interface MusicAsset {
  id: number;
  run_id: string;
  file_path: string;
  modality: string;
  sub_type: string;
  aspect_ratio: string | null;
  seed: number | null;
  created_at: string;
  external_url: string | null;
  prompt_text: string;
}

export interface MusicGenerateResponse {
  run_id: string;
  assets: MusicAsset[];
}

export const musicApi = {
  generate: (data: MusicGenerateParams) =>
    client.post<MusicGenerateResponse>("/music/generate", data).then((r) => r.data),

  generateLyrics: (data: { prompt?: string; mode?: string; title?: string; lyrics?: string }) =>
    client.post<{ song_title: string; style_tags: string; lyrics: string }>("/music/lyrics", data).then((r) => r.data),
};