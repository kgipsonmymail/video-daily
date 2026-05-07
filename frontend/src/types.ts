export interface RunResponse {
  id: string;
  theme: string;
  category: string;
  model: string;
  variant: string | null;
  notes: string | null;
  status: string;
  error_msg: string | null;
  is_favorite: number;
  created_at: string;
  quota_date: string;
  asset_count: number;
}

export interface RunCreate {
  id: string;
  theme?: string;
  category: string;
  model: string;
  variant?: string | null;
  notes?: string | null;
  quota_date: string;
  status?: string;
  error_msg?: string | null;
}

export interface RunUpdate {
  notes?: string | null;
  is_favorite?: boolean | null;
}

export interface AssetResponse {
  id: number;
  run_id: string;
  file_path: string;
  modality: string;
  sub_type: string | null;
  aspect_ratio: string | null;
  seed: number | null;
  created_at: string;
  external_url: string | null;
  theme: string;
  category: string;
  model: string;
  status: string;
  is_favorite: number;
  prompt_text: string;
}

export interface AssetCreate {
  run_id: string;
  file_path: string;
  modality: string;
  sub_type?: string | null;
  aspect_ratio?: string | null;
  seed?: number | null;
}

export interface AssetUpdate {
  external_url?: string | null;
}

export interface PromptResponse {
  id: number;
  text: string;
  lang: string;
  theme: string;
  run_id: string | null;
  created_at: string;
}

export interface PromptCreate {
  text: string;
  lang?: string;
  theme?: string;
  run_id?: string | null;
}

export interface QuotaResponse {
  id: number;
  quota_date: string;
  model: string;
  bucket_name: string;
  daily_limit: number;
  used: number;
  remaining: number;
}

export interface QuotaCreate {
  quota_date: string;
  model: string;
  bucket_name: string;
  daily_limit: number;
}

export type Modality = "all" | "image" | "music" | "video";
export type Page = "tasks" | "queue" | "matrix" | "music" | "query" | "daily" | "voices" | "audio";

export interface TaskQueueResponse {
  id: number;
  task_type: string;
  category: string;
  prompt_text: string;
  model: string;
  modality: string;
  status: string;
  run_id: string | null;
  priority: number;
  error_msg: string | null;
  notes: string | null;
  created_at: string;
  quota_date: string;
}

export interface TaskQueueCreate {
  category: string;
  prompt_text: string;
  model: string;
  notes?: string | null;
  image?: string;
  image2?: string;
}

export interface AutoPromptRequest {
  direction: string;
  theme?: string;
  count?: number;
  categories?: string[];
}

export interface VoiceSampleResponse {
  id: number;
  voice_id: string;
  voice_name: string;
  lang: string;
  model: string;
  script_text: string | null;
  file_path: string;
  file_url: string | null;
  notes: string | null;
  generation_params?: {
    speed?: number;
    vol?: number;
    pitch?: number;
    emotion?: string;
    voice_modify?: { pitch?: number; intensity?: number; timbre?: number; sound_effects?: string };
    audio_setting?: { audio_sample_rate?: number; bitrate?: number; format?: string; channel?: number };
    language_boost?: string;
    model?: string;
  } | null;
  is_favorite: number;
  created_at: string;
}

export interface VoiceSampleCreate {
  voice_id: string;
  voice_name: string;
  lang?: string;
  model?: string;
  script_text?: string | null;
  file_path: string;
  file_url?: string | null;
  notes?: string | null;
}
