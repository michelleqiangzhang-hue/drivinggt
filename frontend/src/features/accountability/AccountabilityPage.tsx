import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { api } from "@/api/client";
import type { BlockRead, LogCreate } from "@/api/types";
import { fmtTime, minutesToLabel } from "@/lib/format";

const CATEGORIES = ["Work", "Study", "Health", "Social", "Chores", "Rest", "Social media", "Other"];
const SUBCATEGORIES: Record<string, string[]> = {
  Work: ["Deep work", "Meetings", "Email / Slack", "Admin", "Other"],
  Study: ["Reading", "Course", "Practice", "Research", "Other"],
  Health: ["Exercise", "Walk", "Meditation", "Meal prep", "Other"],
  Social: ["Friends", "Family", "Date", "Networking", "Other"],
  Chores: ["Cleaning", "Errands", "Cooking", "Laundry", "Other"],
  Rest: ["Nap", "TV / Movies", "Gaming", "Scrolling", "Other"],
  "Social media": ["Instagram", "TikTok", "Twitter / X", "YouTube", "Other"],
  Other: ["Commute", "Waiting", "Unexpected", "Other"],
};

type CheckInStep = "verdict" | "detail" | "done";
type Verdict = "yes" | "partly" | "no";

export default function AccountabilityPage() {
  const qc = useQueryClient();
  const unaccounted = useQuery({
    queryKey: ["unaccounted"],
    queryFn: () => api.unaccountedBlocks(),
  });

  const [currentIdx, setCurrentIdx] = useState(0);
  const [showBlankTime, setShowBlankTime] = useState(false);

  const blocks = unaccounted.data ?? [];
  const activeBlock = blocks[currentIdx] ?? null;

  const advance = useCallback(() => {
    qc.invalidateQueries({ queryKey: ["unaccounted"] });
    qc.invalidateQueries({ queryKey: ["blocks"] });
    qc.invalidateQueries({ queryKey: ["summary"] });
    setCurrentIdx((i) => i + 1);
  }, [qc]);

  if (unaccounted.isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-muted text-sm">Loading…</div>
      </div>
    );
  }

  // Completion state
  if (blocks.length === 0 || currentIdx >= blocks.length) {
    return (
      <div className="space-y-4">
        <CompletionState />
        <button
          className="btn-ghost w-full"
          onClick={() => setShowBlankTime(true)}
        >
          + Log blank time
        </button>
        {showBlankTime && (
          <BlankTimeForm
            onClose={() => setShowBlankTime(false)}
            onDone={() => {
              setShowBlankTime(false);
              qc.invalidateQueries({ queryKey: ["summary"] });
            }}
          />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="card p-4">
        <h2 className="text-lg font-bold">The accountability loop</h2>
        <p className="text-sm text-muted">
          One block at a time. Be honest — it&apos;s private.
        </p>
        <div className="mt-2 flex items-center gap-2">
          <div className="h-1.5 flex-1 rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-brand transition-all"
              style={{ width: `${((currentIdx) / blocks.length) * 100}%` }}
            />
          </div>
          <span className="text-xs text-muted">
            {currentIdx}/{blocks.length}
          </span>
        </div>
      </section>

      <CheckInFlow key={activeBlock!.id} block={activeBlock!} onDone={advance} />

      <button
        className="btn-ghost w-full text-sm"
        onClick={() => setShowBlankTime(true)}
      >
        + Log blank time instead
      </button>
      {showBlankTime && (
        <BlankTimeForm
          onClose={() => setShowBlankTime(false)}
          onDone={() => {
            setShowBlankTime(false);
            qc.invalidateQueries({ queryKey: ["summary"] });
          }}
        />
      )}
    </div>
  );
}

/* ─── Completion State ─── */
function CompletionState() {
  return (
    <div className="card flex flex-col items-center p-8 text-center">
      <div className="mb-3 text-4xl">✨</div>
      <h2 className="text-xl font-bold">All caught up!</h2>
      <p className="mt-2 text-sm text-muted">
        You&apos;ve accounted for every block. The gap between intention and
        reality is now visible. That awareness is the product.
      </p>
    </div>
  );
}

/* ─── One-block check-in flow ─── */
function CheckInFlow({ block, onDone }: { block: BlockRead; onDone: () => void }) {
  const [step, setStep] = useState<CheckInStep>("verdict");
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [what, setWhat] = useState("");
  const [category, setCategory] = useState(block.category);
  const [subcategory, setSubcategory] = useState(block.subcategory ?? "");
  const [description, setDescription] = useState("");
  const [productive, setProductive] = useState(true);
  const [reason, setReason] = useState("");

  const save = useMutation({
    mutationFn: () => {
      const body: LogCreate = {
        block_id: block.id,
        what_happened: what || `Did: ${block.title}`,
        category,
        subcategory: subcategory || null,
        description: description || null,
        productive,
        actual_minutes: block.planned_minutes,
        reason: reason || null,
      };
      return api.createLog(body);
    },
    onSuccess: () => {
      setStep("done");
      setTimeout(onDone, 600);
    },
  });

  function handleVerdict(v: Verdict) {
    setVerdict(v);
    if (v === "yes") {
      setWhat(`Did: ${block.title}`);
      setProductive(true);
    } else if (v === "partly") {
      setWhat("");
      setProductive(true);
    } else {
      setWhat("");
      setProductive(false);
    }
    setStep("detail");
  }

  if (step === "done") {
    return (
      <div className="card flex items-center justify-center p-6">
        <span className="text-good font-semibold">Logged ✓</span>
      </div>
    );
  }

  return (
    <div className="card p-5 space-y-4">
      {/* Block header */}
      <div>
        <div className="flex items-center justify-between">
          <span className="font-bold text-lg">{block.title}</span>
          <span className="pill bg-brand/20 text-brand">
            {fmtTime(block.start)}–{fmtTime(block.end)}
          </span>
        </div>
        <p className="mt-1 text-sm text-muted">
          You blocked {minutesToLabel(block.planned_minutes)} for{" "}
          <span className="font-semibold text-white">{block.category}</span>.
          Did you do it?
        </p>
      </div>

      {/* Step: Verdict */}
      {step === "verdict" && (
        <div className="flex gap-2">
          <button
            className="btn flex-1 bg-good/20 text-good hover:bg-good/30"
            onClick={() => handleVerdict("yes")}
          >
            Yes
          </button>
          <button
            className="btn flex-1 bg-warn/20 text-warn hover:bg-warn/30"
            onClick={() => handleVerdict("partly")}
          >
            Partly
          </button>
          <button
            className="btn flex-1 bg-bad/20 text-bad hover:bg-bad/30"
            onClick={() => handleVerdict("no")}
          >
            No
          </button>
        </div>
      )}

      {/* Step: Detail capture */}
      {step === "detail" && (
        <div className="space-y-3 animate-in fade-in">
          {verdict !== "yes" && (
            <>
              <label className="text-xs text-muted">What actually happened?</label>
              <textarea
                className="input min-h-[70px] resize-none"
                value={what}
                placeholder="Honestly…"
                onChange={(e) => setWhat(e.target.value)}
              />
            </>
          )}

          {/* Category picker */}
          <label className="text-xs text-muted">Category</label>
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                className={`pill transition ${
                  category === c
                    ? "bg-brand text-white"
                    : "bg-white/5 text-muted hover:bg-white/10"
                }`}
                onClick={() => {
                  setCategory(c);
                  setSubcategory("");
                }}
              >
                {c}
              </button>
            ))}
          </div>

          {/* Subcategory */}
          {SUBCATEGORIES[category] && (
            <>
              <label className="text-xs text-muted">Subcategory</label>
              <div className="flex flex-wrap gap-1.5">
                {SUBCATEGORIES[category].map((s) => (
                  <button
                    key={s}
                    className={`pill transition ${
                      subcategory === s
                        ? "bg-brand/80 text-white"
                        : "bg-white/5 text-muted hover:bg-white/10"
                    }`}
                    onClick={() => setSubcategory(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </>
          )}

          {/* Description */}
          <label className="text-xs text-muted">Description (optional)</label>
          <input
            className="input"
            value={description}
            placeholder="Sub-sub detail…"
            onChange={(e) => setDescription(e.target.value)}
          />

          {/* Productive toggle */}
          <div className="flex gap-2">
            <button
              className={`btn flex-1 ${productive ? "bg-good/20 text-good" : "bg-white/5 text-muted"}`}
              onClick={() => setProductive(true)}
            >
              Productive
            </button>
            <button
              className={`btn flex-1 ${!productive ? "bg-bad/20 text-bad" : "bg-white/5 text-muted"}`}
              onClick={() => setProductive(false)}
            >
              Leaked
            </button>
          </div>

          {/* Reason (optional) */}
          {!productive && (
            <>
              <label className="text-xs text-muted">Why did it leak? (optional)</label>
              <input
                className="input"
                value={reason}
                placeholder="Got distracted by…"
                onChange={(e) => setReason(e.target.value)}
              />
            </>
          )}

          {/* Submit */}
          <button
            className="btn-brand w-full mt-2"
            disabled={save.isPending}
            onClick={() => save.mutate()}
          >
            {save.isPending ? "Saving…" : "Log reality"}
          </button>
        </div>
      )}
    </div>
  );
}

/* ─── Blank-time logging ─── */
function BlankTimeForm({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [what, setWhat] = useState("");
  const [category, setCategory] = useState("Other");
  const [subcategory, setSubcategory] = useState("");
  const [productive, setProductive] = useState(false);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");

  const save = useMutation({
    mutationFn: () => {
      const today = new Date().toISOString().slice(0, 10);
      const body: LogCreate = {
        what_happened: what || "Unplanned time",
        category,
        subcategory: subcategory || null,
        productive,
        start: startTime ? `${today}T${startTime}:00` : null,
        end: endTime ? `${today}T${endTime}:00` : null,
      };
      return api.createLog(body);
    },
    onSuccess: onDone,
  });

  return (
    <div className="fixed inset-0 z-30 flex items-end bg-black/60" onClick={onClose}>
      <div
        className="mx-auto w-full max-w-md rounded-t-3xl bg-panel p-5 space-y-3"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold">Log blank time</h3>
        <p className="text-xs text-muted">
          Where did the last few hours go? No block needed.
        </p>

        <div className="flex gap-2">
          <div className="flex-1">
            <label className="text-xs text-muted">From</label>
            <input
              type="time"
              className="input mt-1"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="text-xs text-muted">To</label>
            <input
              type="time"
              className="input mt-1"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
          </div>
        </div>

        <label className="text-xs text-muted">What happened?</label>
        <textarea
          className="input min-h-[60px] resize-none"
          value={what}
          placeholder="I was…"
          onChange={(e) => setWhat(e.target.value)}
        />

        <label className="text-xs text-muted">Category</label>
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              className={`pill transition ${
                category === c
                  ? "bg-brand text-white"
                  : "bg-white/5 text-muted hover:bg-white/10"
              }`}
              onClick={() => {
                setCategory(c);
                setSubcategory("");
              }}
            >
              {c}
            </button>
          ))}
        </div>

        {SUBCATEGORIES[category] && (
          <div className="flex flex-wrap gap-1.5">
            {SUBCATEGORIES[category].map((s) => (
              <button
                key={s}
                className={`pill transition ${
                  subcategory === s
                    ? "bg-brand/80 text-white"
                    : "bg-white/5 text-muted hover:bg-white/10"
                }`}
                onClick={() => setSubcategory(s)}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <button
            className={`btn flex-1 ${productive ? "bg-good/20 text-good" : "bg-white/5 text-muted"}`}
            onClick={() => setProductive(true)}
          >
            Productive
          </button>
          <button
            className={`btn flex-1 ${!productive ? "bg-bad/20 text-bad" : "bg-white/5 text-muted"}`}
            onClick={() => setProductive(false)}
          >
            Leaked
          </button>
        </div>

        <button
          className="btn-brand w-full"
          disabled={save.isPending || !what}
          onClick={() => save.mutate()}
        >
          {save.isPending ? "Saving…" : "Log it"}
        </button>
      </div>
    </div>
  );
}
