import type {
  CreateSessionInput,
  SendMessageInput,
  SessionSnapshot,
} from "@/lib/workbench-types";

const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000";

function getBackendBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_BACKEND_BASE_URL ?? DEFAULT_BACKEND_BASE_URL
  ).replace(/\/$/, "");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBackendBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as { detail?: string };
      throw new Error(payload.detail ?? "请求失败");
    }

    const text = await response.text();
    throw new Error(text || "请求失败");
  }

  return (await response.json()) as T;
}

export function createSession(
  input: CreateSessionInput,
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({
      image_path: input.imagePath,
      ocr_json_path: input.ocrJsonPath,
    }),
  });
}

export function getSession(sessionId: string): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/api/sessions/${sessionId}`);
}

export function sendMessage(
  input: SendMessageInput,
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/api/sessions/${input.sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      message: input.message,
    }),
  });
}

export function rollbackSession(sessionId: string): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/api/sessions/${sessionId}/rollback`, {
    method: "POST",
  });
}
