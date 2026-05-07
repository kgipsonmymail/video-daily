import client from "./client";
import type { VoiceSampleResponse } from "../types";

export interface AudioGenerateParams {
  text: string;
  voice_id: string;
  model?: string;
  speed?: number;
  vol?: number;
  pitch?: number;
  emotion?: string;
  voice_modify?: {
    pitch?: number;
    intensity?: number;
    timbre?: number;
    sound_effects?: string;
  };
  audio_setting?: {
    audio_sample_rate?: number;
    bitrate?: number;
    format?: string;
    channel?: number;
  };
  language_boost?: string;
  pronunciation_dict?: Record<string, string>;
  aigc_watermark?: boolean;
  notes?: string;
}

export interface AudioGenerateResponse {
  id: number;
  file_url: string;
  voice_id: string;
  voice_name: string;
  lang: string;
  model: string;
  script_text: string;
}

export const audioApi = {
  generate: (params: AudioGenerateParams) =>
    client.post<AudioGenerateResponse[]>("/audio/generate", params),
  listHistory: (params?: { lang?: string; limit?: number }) =>
    client.get<VoiceSampleResponse[]>("/audio/history", { params }),
};