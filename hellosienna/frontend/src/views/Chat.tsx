import { useState } from "react";
import { streamChat } from "../api/client";

export function Chat() {
  const [input, setInput] = useState("");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    if (!input.trim() || busy) return;
    setBusy(true);
    setReply("");
    setError(null);
    await streamChat(input, {
      onToken: (t) => setReply((r) => r + t),   // incremental render
      onDone: () => setBusy(false),
      onError: (_code, msg) => {
        setError(msg || "Sienna is unavailable (is Ollama running?)");
        setBusy(false);
      },
    });
  }

  return (
    <section>
      <h2>Chat (M0 pass-through)</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Say hello to Sienna…"
          style={{ flex: 1 }}
        />
        <button onClick={send} disabled={busy}>
          {busy ? "…" : "Send"}
        </button>
      </div>
      {reply && <p data-testid="reply">{reply}</p>}
      {error && <p style={{ color: "crimson" }}>{error}</p>}
    </section>
  );
}
