import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { STATUS_META, categoryColor, fmtTime, minutesToLabel } from "@/lib/format";

function startOfToday(): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}
function endOfToday(): string {
  const d = new Date();
  d.setHours(23, 59, 59, 999);
  return d.toISOString();
}

export default function TodayPage() {
  const blocks = useQuery({
    queryKey: ["blocks", "today"],
    queryFn: () => api.listBlocks(startOfToday(), endOfToday()),
  });
  const summary = useQuery({
    queryKey: ["summary", "day"],
    queryFn: () => api.summary("day"),
  });
  const unaccounted = useQuery({
    queryKey: ["unaccounted"],
    queryFn: () => api.unaccountedBlocks(),
  });

  const adherence = summary.data ? Math.round(summary.data.adherence_rate * 100) : 0;

  return (
    <div className="space-y-4">
      <section className="card p-5">
        <div className="flex items-end justify-between">
          <div>
            <div className="text-sm text-muted">Today's honesty score</div>
            <div className="text-4xl font-extrabold">{adherence}%</div>
            <div className="text-xs text-muted">
              of what you planned, you actually did
            </div>
          </div>
          {summary.data && (
            <div className="text-right text-xs text-muted">
              <div>
                Planned{" "}
                <span className="font-semibold text-white">
                  {minutesToLabel(summary.data.planned_minutes)}
                </span>
              </div>
              <div>
                Logged{" "}
                <span className="font-semibold text-white">
                  {minutesToLabel(summary.data.logged_minutes)}
                </span>
              </div>
              <div className="text-bad">
                {minutesToLabel(summary.data.unproductive_minutes)} leaked
              </div>
            </div>
          )}
        </div>
      </section>

      {(unaccounted.data?.length ?? 0) > 0 && (
        <section className="card border-brand/30 p-4">
          <div className="mb-2 flex items-center justify-between">
            <div className="font-semibold">Account for your time</div>
            <span className="pill bg-brand/20 text-brand">
              {unaccounted.data!.length} pending
            </span>
          </div>
          <p className="mb-3 text-sm text-muted">
            These blocks ended. Tell Bogi what actually happened.
          </p>
          <Link to="/account" className="btn-brand w-full">
            Start check-in
          </Link>
        </section>
      )}

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">Today's plan</h2>
          <Link to="/plan" className="text-sm font-semibold text-brand">
            + Plan
          </Link>
        </div>

        {blocks.isLoading && <div className="text-sm text-muted">Loading…</div>}
        {blocks.data?.length === 0 && (
          <div className="card p-5 text-center text-sm text-muted">
            No blocks yet. Tap <span className="text-brand">Plan</span> and tell Bogi
            what you want to get done.
          </div>
        )}

        {blocks.data?.map((b) => {
          const meta = STATUS_META[b.status];
          return (
            <div key={b.id} className="card flex items-stretch overflow-hidden">
              <div
                className="w-1.5 shrink-0"
                style={{ background: categoryColor(b.category) }}
              />
              <div className="flex-1 p-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold">{b.title}</div>
                  <span className={`pill ${meta.cls}`}>{meta.label}</span>
                </div>
                <div className="text-xs text-muted">
                  {fmtTime(b.start)}–{fmtTime(b.end)} · {b.category} ·{" "}
                  {minutesToLabel(b.planned_minutes)}
                </div>
                {b.log && (
                  <div className="mt-2 rounded-lg bg-black/30 p-2 text-xs">
                    <span className="text-muted">Reality: </span>
                    {b.log.what_happened}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}
