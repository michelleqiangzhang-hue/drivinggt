import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { api } from "@/api/client";
import type { Period } from "@/api/types";
import { categoryColor, minutesToLabel } from "@/lib/format";

const PERIODS: Period[] = ["day", "week", "month", "year"];

/**
 * WORKSTREAM F owns this page. Foundation ships a working summary + category
 * breakdown. F should build the full data bank: trends over time, streaks,
 * per-category adherence history, and the plan-vs-reality gap visualizations.
 */
export default function DataBankPage() {
  const [period, setPeriod] = useState<Period>("day");
  const summary = useQuery({
    queryKey: ["summary", period],
    queryFn: () => api.summary(period),
  });

  const actual = summary.data?.actual_by_category ?? [];

  return (
    <div className="space-y-4">
      <section>
        <h2 className="text-lg font-bold">Your time data bank</h2>
        <p className="text-sm text-muted">
          A private, longitudinal record of how you actually spend your life.
        </p>
      </section>

      <div className="flex gap-2">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`btn flex-1 capitalize ${
              period === p ? "bg-brand text-white" : "bg-white/5 text-muted"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {summary.data && (
        <>
          <section className="card grid grid-cols-3 gap-2 p-4 text-center">
            <Stat label="Planned" value={minutesToLabel(summary.data.planned_minutes)} />
            <Stat
              label="Productive"
              value={minutesToLabel(summary.data.productive_minutes)}
              tone="good"
            />
            <Stat
              label="Leaked"
              value={minutesToLabel(summary.data.unproductive_minutes)}
              tone="bad"
            />
          </section>

          <section className="card p-4">
            <div className="mb-2 text-sm font-bold">Where your time actually went</div>
            {actual.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted">No logs yet.</div>
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={actual} dataKey="minutes" nameKey="category" outerRadius={90}>
                      {actual.map((c) => (
                        <Cell key={c.category} fill={categoryColor(c.category)} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v: number, n: string) => [minutesToLabel(v), n]}
                      contentStyle={{ background: "#1f232c", border: "none", borderRadius: 12 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              {actual.map((c) => (
                <span key={c.category} className="pill bg-white/5 text-muted">
                  <span
                    className="mr-1 inline-block h-2 w-2 rounded-full"
                    style={{ background: categoryColor(c.category) }}
                  />
                  {c.category} · {minutesToLabel(c.minutes)}
                </span>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "bad";
}) {
  const color = tone === "good" ? "text-good" : tone === "bad" ? "text-bad" : "text-white";
  return (
    <div>
      <div className={`text-xl font-extrabold ${color}`}>{value}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}
