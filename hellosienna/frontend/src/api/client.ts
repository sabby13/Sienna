// API client — the ONLY module that talks to the backend (frozen invariant).
// Change 1: the per-launch token travels ONLY as the X-HS-Token header, never in a
// URL/query string, and is never persisted (read from in-memory window.__HS_TOKEN__).

declare global {
  interface Window {
    __HS_TOKEN__?: string;
  }
}

const TOKEN_HEADER = "X-HS-Token";

export function getToken(): string {
  return (typeof window !== "undefined" && window.__HS_TOKEN__) || "";
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return { [TOKEN_HEADER]: getToken(), ...extra };
}

export async function health(): Promise<{ status: string; version: string }> {
  const r = await fetch("/api/health", { headers: authHeaders() });
  if (!r.ok) throw new Error(`health ${r.status}`);
  return r.json();
}

export interface ModelStatus {
  ollama_reachable: boolean;
  chat_model: string;
  chat_model_present: boolean;
  embed_model: string;
  embed_model_present: boolean;
  detail: string | null;
}

export async function modelStatus(): Promise<ModelStatus> {
  const r = await fetch("/api/model/status", { headers: authHeaders() });
  if (!r.ok) throw new Error(`model/status ${r.status}`);
  return r.json();
}

export interface ChatCallbacks {
  onToken: (text: string) => void;
  onDone?: () => void;
  onError?: (code: string, message: string) => void;
}

// Parse an SSE byte stream into (event, data) pairs and dispatch to callbacks.
export async function streamChat(message: string, cb: ChatCallbacks): Promise<void> {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ message }),
  });
  if (!resp.ok || !resp.body) {
    cb.onError?.("http_error", `chat ${resp.status}`);
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const frames = buf.split("\n\n");
    buf = frames.pop() ?? ""; // keep the incomplete trailing frame
    for (const frame of frames) dispatchFrame(frame, cb);
  }
  if (buf.trim()) dispatchFrame(buf, cb);
}

function dispatchFrame(frame: string, cb: ChatCallbacks): void {
  if (!frame.trim() || frame.startsWith(":")) return; // comment/keepalive
  let event = "";
  let data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (event === "token") {
    const obj = data ? JSON.parse(data) : {};
    if (obj.text) cb.onToken(obj.text);
  } else if (event === "done") {
    cb.onDone?.();
  } else if (event === "error") {
    const obj = data ? JSON.parse(data) : {};
    cb.onError?.(obj.code ?? "error", obj.message ?? "");
  }
}
