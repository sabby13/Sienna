import { useEffect, useState } from "react";
import { health, modelStatus, type ModelStatus } from "./api/client";
import { Chat } from "./views/Chat";

export default function App() {
  const [backend, setBackend] = useState("checking…");
  const [model, setModel] = useState<ModelStatus | null>(null);

  useEffect(() => {
    health()
      .then((h) => setBackend(`ok · v${h.version}`))
      .catch(() => setBackend("unreachable"));
    modelStatus()
      .then(setModel)
      .catch(() => setModel(null));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>HelloSienna — M0</h1>
      <p>backend: <strong data-testid="backend-status">{backend}</strong></p>
      <p>
        Ollama:{" "}
        <strong>
          {model ? (model.ollama_reachable ? "reachable" : "unavailable") : "…"}
        </strong>
        {model && model.ollama_reachable && (
          <> · chat model {model.chat_model_present ? "present" : "missing"}</>
        )}
      </p>
      <Chat />
    </main>
  );
}
