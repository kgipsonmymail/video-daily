import client from "./client";

export interface MatrixConfig {
  id: number;
  name: string;
  subjects_text: string;
  styles_text: string;
  theme: string;
  notes: string | null;
  created_at: string;
  prompt_base?: string;
}

export interface MatrixAsset {
  id: number;
  run_id: string;
  file_path: string;
  modality: string;
  sub_type: string;
  aspect_ratio: string | null;
  seed: number | null;
  created_at: string;
  external_url: string | null;
  variant: string;
  category: string;
  model: string;
  status: string;
  prompt_text: string;
}

export interface MusicMatrixConfig {
  id: number;
  name: string;
  prompts_text: string;
  theme: string;
  notes: string | null;
  created_at: string;
}

export interface MusicTrack {
  row: number;
  col: number;
  prompt: string;
  file_path: string;
  status: string;
  error?: string | null;
}

export const matrixApi = {
  listConfigs: () =>
    client.get<MatrixConfig[]>("/matrix/configs").then((r) => r.data),

  createConfig: (data: { name: string; subjects_text: string; styles_text: string; theme?: string; notes?: string; prompt_base?: string }) =>
    client.post<MatrixConfig>("/matrix/configs", data).then((r) => r.data),

  deleteConfig: (id: number) =>
    client.delete(`/matrix/configs/${id}`),

  getConfigAssets: (configId: number) =>
    client.get<MatrixAsset[]>(`/matrix/configs/${configId}/assets`).then((r) => r.data),

  // Music matrix
  listMusicConfigs: () =>
    client.get<MusicMatrixConfig[]>("/matrix/music/configs").then((r) => r.data),

  generateMusicMatrix: (data: { name: string; row_styles: string[]; col_styles: string[]; base_prompt?: string; notes?: string }) =>
    client.post<{ config_id: number; total: number; message: string }>("/matrix/music/generate", data).then((r) => r.data),

  getMusicConfigTracks: (configId: number) =>
    client.get<MusicTrack[]>(`/matrix/music/configs/${configId}/tracks`).then((r) => r.data),

  deleteMusicConfig: (id: number) =>
    client.delete(`/matrix/music/configs/${id}`),

  retryMusicMatrix: (configId: number) =>
    client.post(`/matrix/music/retry/${configId}`).then((r) => r.data),
};
