import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import type { BlockRead } from "@/api/types";
import { fmtTime, minutesToLabel } from "@/lib/format";

/**
 * WORKSTREAM E owns this page (with the coach page). Foundation ships a working
 * block-by-block check-in. E should add the conversational "Hey Boogie" check-in,
 * blank-time logging, and richer category/subcategory pickers.
 */
export default function AccountabilityPage() {
  const qc = useQueryClient();
  const unaccounted = useQuery({
    queryKey: ["unaccounted"],
    queryFn: () => api.unaccountedBlocks(),
  });

  const [active, setActive] = useState<BlockRead | null>(null);

  return (
    <div className="space-y-4">
      <section className="card p-4">
        <h2 className="text-lg font-bold">The accountability loop</h2>
        <p className="text-sm text-muted">
          Your calendar said one thing. What actually happened? Be honest — it's
          private, and it's the whole point.
        </p>
      </section>

      {unaccounted.data?.length === 0 && (
        <div className="card p-5 text-center text-sm text-muted">
          You're all caught up. Nothing to account for right now.
        </div>
      )}

      {unaccounted.data?.map((b) => (
        <div key={b.id} className="card p-4">
          <div className="flex items-center justify-between">
            <div className="font-semibold">{b.title}</div>
            <span className="text-xs text-muted">
              {fmtTime(b.start)}–{fmtTime(b.end)} · {minutesToLabel(b.planned_minutes)}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted">
            You blocked this for <b>{b.category}</b>. Did you do it?
          </p>
          <button className="btn-brand mt-3 w-full" onClick={() => setActive(b)}>
            Account for it
          </button>
        </div>
      ))}

      {active && (
        <CheckInForm
          block={active}
          onClose={() => setActive(null)}
          onDone={() => {
            setActive(null);
            qc.invalidateQueries({ queryKey: ["unaccounted"] });
            qc.invalidateQueries({ queryKey: ["blocks"] });
            qc.invalidateQueries({ queryKey: ["summary"] });
          }}
        />
      )}
    </div>
  );
}

function CheckInForm({
  block,
  onClose,
  onDone,
}: {
  block: BlockRead;
  onClose: () => void;
  onDone: () => void;
}) {
  const [what, setWhat] = useState("");
  const [productive, setProductive] = useState(true);
  const [category, setCategory] = useState(block.category);

  const save = useMutation({
    mutationFn: () =>
      api.createLog({
        block_id: block.id,
        what_happened: what || `Did: ${block.title}`,
        category,
        productive,
        actual_minutes: block.planned_minutes,
      }),
    onSuccess: onDone,
  });

  return (
    <div className="fixed inset-0 z-30 flex items-end bg-black/60" onClick={onClose}>
      <div
        className="mx-auto w-full max-w-md rounded-t-3xl bg-panel p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 text-lg font-bold">{block.title}</div>
        <label className="text-xs text-muted">What actually happened?</label>
        <textarea
          className="input mt-1 min-h-[80px] resize-none"
          value={what}
          placeholder="Honestly…"
          onChange={(e) => setWhat(e.target.value)}
        />
        <label className="mt-3 block text-xs text-muted">Category</label>
        <input className="input mt-1" value={category} onChange={(e) => setCategory(e.target.value)} />
        <div className="mt-3 flex gap-2">
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
            Leaked time
          </button>
        </div>
        <button className="btn-brand mt-4 w-full" disabled={save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "Saving…" : "Log reality"}
        </button>
      </div>
    </div>
  );
}
