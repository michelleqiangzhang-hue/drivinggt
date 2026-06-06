import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import type { ChatMessage } from "@/api/types";

const QUICK_CHIPS = [
  "Plan my day",
  "What did I actually do today?",
  "Where did my time go this week?",
  "Help me stay focused",
];

interface SpeechRecognitionEvent {
  results: { [index: number]: { [index: number]: { transcript: string } } };
}

export default function CoachPage() {
  const [convId, setConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hey! I'm Bogi — your accountability coach. I help you plan concrete blocks, then hold you to them. What's on your mind?",
    },
  ]);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef<unknown>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Check Speech API support
  useEffect(() => {
    const w = window as unknown as Record<string, unknown>;
    const SpeechRecognition = w.SpeechRecognition || w.webkitSpeechRecognition;
    setSpeechSupported(!!SpeechRecognition);
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useMutation({
    mutationFn: (msg: string) => api.chat({ conversation_id: convId, message: msg }),
    onSuccess: (res) => {
      setConvId(res.conversation_id);
      if (res.history.length) {
        setMessages(res.history);
      } else {
        setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      }
    },
  });

  const submit = useCallback(
    (text?: string) => {
      const msg = (text ?? input).trim();
      if (!msg) return;
      setMessages((m) => [...m, { role: "user", content: msg }]);
      setInput("");
      send.mutate(msg);
    },
    [input, send],
  );

  function toggleMic() {
    if (listening) {
      stopListening();
      return;
    }

    const w = window as unknown as Record<string, unknown>;
    const SpeechRecognition = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition = new (SpeechRecognition as any)();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      setListening(false);
    };

    recognition.onerror = () => {
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  function stopListening() {
    if (recognitionRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (recognitionRef.current as any).stop();
    }
    setListening(false);
  }

  return (
    <div className="flex h-[calc(100vh-200px)] flex-col">
      {/* Messages */}
      <div className="flex-1 space-y-3 overflow-y-auto pb-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
              m.role === "user"
                ? "ml-auto bg-brand text-white"
                : "bg-panel2 text-white"
            }`}
          >
            {m.role === "assistant" && (
              <span className="mb-0.5 block text-[10px] font-bold uppercase tracking-wide text-brand">
                Bogi
              </span>
            )}
            {m.content}
          </div>
        ))}
        {send.isPending && (
          <div className="max-w-[60%] rounded-2xl bg-panel2 px-4 py-2.5 text-sm text-muted">
            <span className="inline-flex gap-1">
              <span className="animate-bounce">·</span>
              <span className="animate-bounce [animation-delay:0.1s]">·</span>
              <span className="animate-bounce [animation-delay:0.2s]">·</span>
            </span>{" "}
            Bogi is thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick-action chips */}
      {messages.length <= 1 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {QUICK_CHIPS.map((chip) => (
            <button
              key={chip}
              className="pill bg-brand/10 text-brand hover:bg-brand/20 transition cursor-pointer"
              onClick={() => submit(chip)}
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <div className="flex items-center gap-2">
        <input
          className="input"
          placeholder="Talk to Bogi…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />

        {/* Mic button */}
        {speechSupported && (
          <button
            className={`btn shrink-0 rounded-full p-2 ${
              listening
                ? "bg-bad/20 text-bad animate-pulse"
                : "bg-white/5 text-muted hover:bg-white/10"
            }`}
            onClick={toggleMic}
            title={listening ? "Stop listening" : "Voice input"}
            aria-label={listening ? "Stop listening" : "Voice input"}
          >
            <MicIcon />
          </button>
        )}

        <button
          className="btn-brand shrink-0"
          onClick={() => submit()}
          disabled={send.isPending || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}

function MicIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" x2="12" y1="19" y2="22" />
    </svg>
  );
}
