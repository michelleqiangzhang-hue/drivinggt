import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { categoryColor, fmtTime, minutesToLabel } from "@/lib/format";

/**
 * WORKSTREAM D owns this page. Foundation ships a working natural-language planner
 * and block list. D should build the rich day/hourly timeline view, drag-to-create,
 * inline editing, and the plan-vs-reality overlay.
 */
export default function CalendarPage() {
  const qc = useQueryClient();
  const [text, setText] = useState("");

  const blocks = useQuery({ queryKey: ["blocks", "all"], queryFn: () => api.listBlocks() });

  const plan = useMutation({
    mutationFn: (t: string) => api.planDay({ text: t }),
    onSuccess: () => {
      setText("");
      qc.invalidateQueries({ queryKey: ["blocks"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
    },
  });

  return (
    <div className="space-y-4">
      <section className="card p-4">
        <h2 className="mb-1 text-lg font-bold">Plan your day</h2>
        <p className="mb-3 text-sm text-muted">
          Tell Bogi in plain words. Be concrete: “edit videos for 2 hours, email
          manufacturers for 45 min.”
        </p>
        <textarea
          className="input min-h-[90px] resize-none"
          placeholder="e.g. record podcast for 1 hour, edit videos for 2 hours…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          className="btn-brand mt-3 w-full"
          disabled={!text.trim() || plan.isPending}
          onClick={() => plan.mutate(text)}
        >
          {plan.isPending ? "Planning…" : "Turn into blocks"}
        </button>
        {plan.data && (
          <div className="mt-3 rounded-xl bg-brand/10 p-3 text-sm text-brand">
            {plan.data.message}
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-bold uppercase tracking-wide text-muted">
          Your blocks
        </h3>
        {blocks.data?.map((b) => (
          <div key={b.id} className="card flex items-center gap-3 p-3">
            <div
              className="h-9 w-1.5 rounded-full"
              style={{ background: categoryColor(b.category) }}
            />
            <div className="flex-1">
              <div className="font-semibold">{b.title}</div>
              <div className="text-xs text-muted">
                {fmtTime(b.start)}–{fmtTime(b.end)} · {minutesToLabel(b.planned_minutes)}
              </div>
            </div>
            <button
              className="text-xs text-muted hover:text-bad"
              onClick={() =>
                api.deleteBlock(b.id).then(() => qc.invalidateQueries({ queryKey: ["blocks"] }))
              }
            >
              Delete
            </button>
          </div>
        ))}
        {blocks.data?.length === 0 && (
          <div className="card p-5 text-center text-sm text-muted">No blocks yet.</div>
        )}
      </section>
    </div>
  );
}
