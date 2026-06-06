import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import type { ChatMessage } from "@/api/types";

/**
 * WORKSTREAM E owns this page (with accountability). Foundation ships a working
 * chat loop against the coach API. E should add the "Hey Boogie" voice interface
 * (Web Speech API), conversation history, and quick-action chips.
 */
export default function CoachPage() {
  const [convId, setConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hey, I'm Bogi. I help you plan concrete blocks, then hold you to them. What's on your mind?",
    },
  ]);
  const [input, setInput] = useState("");

  const send = useMutation({
    mutationFn: (msg: string) => api.chat({ conversation_id: convId, message: msg }),
    onSuccess: (res) => {
      setConvId(res.conversation_id);
      setMessages(res.history.length ? res.history : messages);
    },
  });

  function submit() {
    const msg = input.trim();
    if (!msg) return;
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setInput("");
    send.mutate(msg);
  }

  return (
    <div className="flex h-[calc(100vh-200px)] flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto pb-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
              m.role === "user"
                ? "ml-auto bg-brand text-white"
                : "bg-panel2 text-white"
            }`}
          >
            {m.content}
          </div>
        ))}
        {send.isPending && (
          <div className="bg-panel2 max-w-[60%] rounded-2xl px-4 py-2 text-sm text-muted">
            Bogi is thinking…
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <input
          className="input"
          placeholder="Talk to Bogi…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        <button className="btn-brand shrink-0" onClick={submit} disabled={send.isPending}>
          Send
        </button>
      </div>
    </div>
  );
}
