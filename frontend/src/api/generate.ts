import client from "./client";

export const generateApi = {
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return client.post<{ file_path: string; url: string }>("/generate/upload", form).then((r) => r.data);
  },
  image: (data: {
    prompt: string;
    model?: string;
    aspect_ratio?: string;
    n?: number;
    variant?: string;
    theme?: string;
    config_id?: number | null;
    matrix_name?: string | null;
  }) =>
    client.post<{
      run_id: string;
      assets: Array<{
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
      }>;
    }>("/generate/image", data).then((r) => r.data),
};
