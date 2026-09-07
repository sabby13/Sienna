import { afterEach, describe, expect, it, vi } from "vitest";
import { health, streamChat } from "./client";

const TOKEN = "TOKEN123-secret";

function sseResponse(body: string): Response {
  const enc = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      c.enqueue(enc.encode(body));
      c.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("API client (Change 1: header-only token)", () => {
  it("sends X-HS-Token header and never puts the token in the URL", async () => {
    window.__HS_TOKEN__ = TOKEN;
    const calls: { url: string; init?: RequestInit }[] = [];
    vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
      calls.push({ url, init });
      return Promise.resolve(new Response(JSON.stringify({ status: "ok", version: "0.0.1+m0" }),
        { status: 200, headers: { "Content-Type": "application/json" } }));
    });

    await health();

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe("/api/health");
    expect(calls[0].url).not.toContain(TOKEN); // token never in URL/query
    const headers = calls[0].init!.headers as Record<string, string>;
    expect(headers["X-HS-Token"]).toBe(TOKEN);
  });

  it("parses an SSE stream into incremental tokens then done", async () => {
    window.__HS_TOKEN__ = TOKEN;
    const body =
      'event: token\ndata: {"text":"Hello"}\n\n' +
      'event: token\ndata: {"text":", Sahib"}\n\n' +
      "event: done\ndata: {}\n\n";
    let capturedUrl = "";
    vi.stubGlobal("fetch", (url: string, init?: RequestInit) => {
      capturedUrl = url;
      const headers = init!.headers as Record<string, string>;
      expect(headers["X-HS-Token"]).toBe(TOKEN);
      return Promise.resolve(sseResponse(body));
    });

    const tokens: string[] = [];
    let done = false;
    await streamChat("hi", {
      onToken: (t) => tokens.push(t),
      onDone: () => (done = true),
    });

    expect(capturedUrl).toBe("/api/chat");
    expect(capturedUrl).not.toContain(TOKEN);
    expect(tokens).toEqual(["Hello", ", Sahib"]);
    expect(done).toBe(true);
  });

  it("dispatches SSE error frames to onError", async () => {
    window.__HS_TOKEN__ = TOKEN;
    const body = 'event: error\ndata: {"code":"provider_unavailable","message":"no ollama"}\n\n';
    vi.stubGlobal("fetch", () => Promise.resolve(sseResponse(body)));

    let errCode = "";
    await streamChat("hi", { onToken: () => {}, onError: (c) => (errCode = c) });
    expect(errCode).toBe("provider_unavailable");
  });
});
