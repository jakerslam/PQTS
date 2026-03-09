"use client";

import { useMemo, useState } from "react";

import type { AssistantTurnResponse, ChatTurn } from "@/lib/chat/types";

function nowIso(): string {
  return new Date().toISOString();
}

function turnId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export function AssistantConsole() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [lastSubmitted, setLastSubmitted] = useState<{
    text: string;
    timestampMs: number;
  } | null>(null);

  const sendingCount = useMemo(
    () => turns.filter((turn) => turn.status === "pending").length,
    [turns],
  );

  async function submitTurn() {
    const content = input.trim();
    if (!content || isSending) {
      return;
    }
    if (
      lastSubmitted &&
      lastSubmitted.text === content &&
      Date.now() - lastSubmitted.timestampMs < 8000
    ) {
      return;
    }

    const userTurnId = turnId("user");
    const assistantTurnId = turnId("assistant");
    const createdAt = nowIso();

    const userTurn: ChatTurn = {
      id: userTurnId,
      role: "user",
      text: content,
      status: "sent",
      createdAt,
    };
    const assistantOptimistic: ChatTurn = {
      id: assistantTurnId,
      role: "assistant",
      text: "",
      status: "pending",
      createdAt,
    };

    setInput("");
    setTurns((prev) => [...prev, userTurn, assistantOptimistic]);
    setIsSending(true);
    setLastSubmitted({ text: content, timestampMs: Date.now() });

    try {
      const response = await fetch("/api/assistant/turn", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: content }),
      });
      if (!response.ok) {
        throw new Error(`assistant route returned ${response.status}`);
      }
      const payload = (await response.json()) as AssistantTurnResponse;

      // Reconciliation success path: replace optimistic assistant placeholder with final response.
      setTurns((prev) =>
        prev.map((turn) => {
          if (turn.id !== assistantTurnId) return turn;
          return {
            ...turn,
            status: "sent",
            text: payload.assistant_message,
          };
        }),
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown error";

      // Reconciliation failure path: drop pending assistant turn and mark user turn as errored.
      setTurns((prev) =>
        prev
          .filter((turn) => turn.id !== assistantTurnId)
          .map((turn) => {
            if (turn.id !== userTurnId) return turn;
            return { ...turn, status: "error", errorMessage: message };
          }),
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="card" style={{ display: "grid", gap: 12 }}>
      <h2 style={{ margin: 0 }}>Assistant Console</h2>
      <p style={{ margin: 0, color: "var(--muted)" }}>
        Optimistic turns: {sendingCount} pending
      </p>

      <div
        style={{
          border: "1px solid var(--border)",
          borderRadius: 8,
          minHeight: 180,
          maxHeight: 360,
          overflowY: "auto",
          padding: 12,
          display: "grid",
          gap: 10,
        }}
      >
        {turns.length === 0 ? (
          <p style={{ margin: 0, color: "var(--muted)" }}>No turns yet.</p>
        ) : (
          turns.map((turn) => (
            <article key={turn.id} className="card" style={{ padding: 10 }}>
              <p style={{ margin: 0, fontSize: 12, color: "var(--muted)" }}>
                {turn.role.toUpperCase()} · {turn.status}
              </p>
              <p style={{ margin: "6px 0 0" }}>{turn.text || "..."}</p>
              {turn.errorMessage ? (
                <p style={{ margin: "6px 0 0", color: "#b42318" }}>{turn.errorMessage}</p>
              ) : null}
            </article>
          ))
        )}
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== "Enter") {
              return;
            }
            if (event.shiftKey) {
              return;
            }
            event.preventDefault();
            void submitTurn();
          }}
          rows={4}
          placeholder="Ask for a risk summary..."
        />
        <button type="button" onClick={submitTurn} disabled={isSending}>
          {isSending ? "Sending..." : "Send"}
        </button>
      </div>
    </section>
  );
}
