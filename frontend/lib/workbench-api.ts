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
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${getBackendBaseUrl()}${path}`, {
    ...init,
    headers,
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
  const formData = new FormData();
  formData.append("image", input.image);
  return request<SessionSnapshot>("/api/sessions", {
    method: "POST",
    body: formData,
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
