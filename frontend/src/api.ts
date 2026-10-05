export interface Named {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}
export interface Audio extends Named {
  path: string;
  size: number;
}
export interface Role extends Named {
  tags: string[];
  audio_ids: string[];
}
export interface Binding {
  speaker: string;
  role_id: string | null;
  audio_id: string | null;
}
export interface Generation {
  mode: "normal" | "fast";
  do_sample: boolean;
  top_p: number;
  top_k: number;
  temperature: number;
  length_penalty: number;
  num_beams: number;
  repetition_penalty: number;
  max_mel_tokens: number;
  max_text_tokens_per_sentence: number;
  sentences_bucket_max_size: number;
}
export const defaults: Generation = {
  mode: "normal",
  do_sample: true,
  top_p: 0.8,
  top_k: 30,
  temperature: 1,
  length_penalty: 0,
  num_beams: 3,
  repetition_penalty: 10,
  max_mel_tokens: 600,
  max_text_tokens_per_sentence: 120,
  sentences_bucket_max_size: 4,
};
export interface Take {
  id: string;
  take_index: number;
  audio_id: string | null;
  created_at: string;
  snapshot: {
    text: string;
    speaker: string;
    audio_id: string | null;
    generation: Generation;
  };
  missing?: boolean;
}
export interface Line {
  id: string;
  index: number;
  text: string;
  speaker: string;
  takes: Take[];
  current_take_id: string | null;
  revision: number;
  selection_revision: number;
}
export interface Preset extends Named {
  bindings: Binding[];
  generation: Generation;
}
export interface Session extends Preset {
  project_id: string;
  interval: number;
  lines: Line[];
  text: string;
  outputs: string[];
  line_count?: number;
}
export interface Task extends Named {
  kind: string;
  status: string;
  progress: number;
  message: string;
  error: string | null;
  result: Audio | null;
  session_ids: string[];
}
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    headers:
      data instanceof FormData ? {} : { "Content-Type": "application/json" },
    body:
      data === undefined
        ? undefined
        : data instanceof FormData
          ? data
          : JSON.stringify(data),
    signal,
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  }
  return response.json();
}
export const fileUrl = (id: string, download = false) =>
  `/api/audio/${id}/file${download ? "?download=true" : ""}`;
export const sessionInput = (s: Session) => ({
  name: s.name,
  project_id: s.project_id,
  bindings: s.bindings,
  generation: s.generation,
  interval: s.interval,
});
