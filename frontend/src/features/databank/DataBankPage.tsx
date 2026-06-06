import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  addDays,
  addMonths,
  addWeeks,
  addYears,
  subDays,
  subMonths,
  subWeeks,
  subYears,
  format,
} from "date-fns";

import { api } from "@/api/client";
import type { GoalRead, PatternRead, Period } from "@/api/types";
import { categoryColor, minutesToLabel } from "@/lib/format";

const PERIODS: Period[] = ["day", "week", "month", "year"];

function anchorLabel(period: Period, anchor: Date): string {
  switch (period) {
    case "day":
      return format(anchor, "EEE, MMM d");
    case "week":
      return `Week of ${format(anchor, "MMM d")}`;
    case "month":
      return format(anchor, "MMMM yyyy");
    case "year":
      return format(anchor, "yyyy");
  }
}

function shiftAnchor(anchor: Date, period: Period, dir: -1 | 1): Date {
  switch (period) {
    case "day":
      return dir === -1 ? subDays(anchor, 1) : addDays(anchor, 1);
    case "week":
      return dir === -1 ? subWeeks(anchor, 1) : addWeeks(anchor, 1);
    case "month":
      return dir === -1 ? subMonths(anchor, 1) : addMonths(anchor, 1);
    case "year":
      return dir === -1 ? subYears(anchor, 1) : addYears(anchor, 1);
  }
}

export default function DataBankPage() {
  const [period, setPeriod] = useState<Period>("day");
  const [anchor, setAnchor] = useState<Date>(new Date());

  const anchorISO = anchor.toISOString().slice(0, 10);

  const summary = useQuery({
    queryKey: ["summary", period, anchorISO],
    queryFn: () => api.summary(period, anchorISO),
  });

  const goals = useQuery({
    queryKey: ["goals"],
    queryFn: () => api.listGoals(),
    enabled: period === "month" || period === "year",
  });

  const patterns = useQuery({
    queryKey: ["patterns"],
    queryFn: () => api.listPatterns(),
    enabled: period === "month" || period === "year",
  });

  const actual = summary.data?.actual_by_category ?? [];

  const comparisonData = useMemo(() => {
    if (!summary.data) return [];
    const planned = summary.data.planned_by_category;
    const logged = summary.data.actual_by_category;
    const cats = new Set([
      ...planned.map((p) => p.category),
      ...logged.map((l) => l.category),
    ]);
    return Array.from(cats).map((cat) => ({
      category: cat,
      planned: planned.find((p) => p.category === cat)?.minutes ?? 0,
      actual: logged.find((l) => l.category === cat)?.minutes ?? 0,
    }));
  }, [summary.data]);

  const adherence = summary.data
    ? Math.round(summary.data.adherence_rate * 100)
    : 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <section>
        <h2 className="text-lg font-bold">Your time data bank</h2>
        <p className="text-sm text-muted">
          A private, longitudinal record of how you actually spend your life.
        </p>
      </section>

      {/* Period switcher */}
      <div className="flex gap-2">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => {
              setPeriod(p);
              setAnchor(new Date());
            }}
            className={`btn flex-1 capitalize ${
              period === p ? "bg-brand text-white" : "bg-white/5 text-muted"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Anchor navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setAnchor(shiftAnchor(anchor, period, -1))}
          className="btn-ghost px-3 py-1 text-sm"
        >
          ←
        </button>
        <span className="text-sm font-semibold">
          {anchorLabel(period, anchor)}
        </span>
        <button
          onClick={() => setAnchor(shiftAnchor(anchor, period, 1))}
          className="btn-ghost px-3 py-1 text-sm"
        >
          →
        </button>
      </div>

      {summary.isLoading && (
        <div className="text-center text-sm text-muted">Loading…</div>
      )}

      {summary.data && (
        <>
          {/* Adherence headline card */}
          <section className="card p-5">
            <div className="flex items-end justify-between">
              <div>
                <div className="text-sm text-muted">Honesty / adherence</div>
                <div className="text-4xl font-extrabold">{adherence}%</div>
                <div className="text-xs text-muted">
                  of what you planned, you actually did
                </div>
              </div>
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
            </div>
            {/* Block status summary */}
            <div className="mt-3 flex gap-2 flex-wrap">
              <span className="pill bg-good/20 text-good">
                {summary.data.completed_blocks} completed
              </span>
              <span className="pill bg-warn/20 text-warn">
                {summary.data.partial_blocks} partial
              </span>
              <span className="pill bg-bad/20 text-bad">
                {summary.data.missed_blocks} missed
              </span>
              <span className="pill bg-white/10 text-muted">
                {summary.data.unlogged_blocks} unlogged
              </span>
            </div>
          </section>

          {/* Plan vs Reality comparison bars */}
          <section className="card p-4">
            <div className="mb-2 text-sm font-bold">
              Plan vs reality — per category
            </div>
            {comparisonData.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted">
                No data yet for this period.
              </div>
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={comparisonData}
                    margin={{ top: 8, right: 8, left: 0, bottom: 4 }}
                  >
                    <XAxis
                      dataKey="category"
                      tick={{ fill: "#8b93a7", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: "#8b93a7", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v: number) => minutesToLabel(v)}
                    />
                    <Tooltip
                      formatter={(v: number, n: string) => [
                        minutesToLabel(v),
                        n === "planned" ? "Planned" : "Actual",
                      ]}
                      contentStyle={{
                        background: "#1f232c",
                        border: "none",
                        borderRadius: 12,
                      }}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: 11, color: "#8b93a7" }}
                    />
                    <Bar
                      dataKey="planned"
                      name="Planned"
                      fill="#7c5cff"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="actual"
                      name="Actual"
                      fill="#5b8cff"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </section>

          {/* Pie chart: where time actually went */}
          <section className="card p-4">
            <div className="mb-2 text-sm font-bold">
              Where your time actually went
            </div>
            {actual.length === 0 ? (
              <div className="py-6 text-center text-sm text-muted">
                No logs yet.
              </div>
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={actual}
                      dataKey="minutes"
                      nameKey="category"
                      outerRadius={90}
                    >
                      {actual.map((c) => (
                        <Cell
                          key={c.category}
                          fill={categoryColor(c.category)}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v: number, n: string) => [
                        minutesToLabel(v),
                        n,
                      ]}
                      contentStyle={{
                        background: "#1f232c",
                        border: "none",
                        borderRadius: 12,
                      }}
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

          {/* Goals & Patterns — month/year only */}
          {(period === "month" || period === "year") && (
            <>
              <GoalsSection goals={goals.data ?? []} period={period} />
              <PatternsSection patterns={patterns.data ?? []} />
            </>
          )}
        </>
      )}
    </div>
  );
}

function GoalsSection({
  goals,
  period,
}: {
  goals: GoalRead[];
  period: Period;
}) {
  if (goals.length === 0) {
    return (
      <section className="card p-4">
        <div className="text-sm font-bold mb-2">Goals</div>
        <div className="py-4 text-center text-sm text-muted">
          No goals set yet. Use the coach to set honest goals.
        </div>
      </section>
    );
  }

  return (
    <section className="card p-4 space-y-3">
      <div className="text-sm font-bold">
        Your {period === "month" ? "monthly" : "yearly"} goals
      </div>
      {goals.map((g) => (
        <div
          key={g.id}
          className="flex items-start gap-3 rounded-xl bg-black/20 p-3"
        >
          <span className="mt-0.5 text-lg">
            {g.achieved === true ? "✓" : g.achieved === false ? "✗" : "◌"}
          </span>
          <div className="flex-1">
            <div className="text-sm font-semibold">{g.title}</div>
            <div className="text-xs text-muted">
              {g.horizon}
              {g.target_category && ` · ${g.target_category}`}
            </div>
          </div>
          <span
            className={`pill ${
              g.achieved === true
                ? "bg-good/20 text-good"
                : g.achieved === false
                  ? "bg-bad/20 text-bad"
                  : "bg-white/10 text-muted"
            }`}
          >
            {g.achieved === true
              ? "Achieved"
              : g.achieved === false
                ? "Missed"
                : "In progress"}
          </span>
        </div>
      ))}
    </section>
  );
}

function PatternsSection({ patterns }: { patterns: PatternRead[] }) {
  if (patterns.length === 0) {
    return (
      <section className="card p-4">
        <div className="text-sm font-bold mb-2">Learned patterns</div>
        <div className="py-4 text-center text-sm text-muted">
          Bogi hasn't found any patterns yet. Keep logging and they'll emerge.
        </div>
      </section>
    );
  }

  return (
    <section className="card p-4 space-y-3">
      <div className="text-sm font-bold">Honest callouts from your data</div>
      {patterns.map((p) => (
        <div key={p.id} className="rounded-xl bg-black/20 p-3">
          <div className="flex items-center gap-2 mb-1">
            {p.category && (
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: categoryColor(p.category) }}
              />
            )}
            <span className="text-sm font-semibold">{p.summary}</span>
            <span className="pill bg-white/10 text-muted ml-auto">
              {Math.round(p.confidence * 100)}% sure
            </span>
          </div>
          {p.suggestion && (
            <div className="text-xs text-muted mt-1">💡 {p.suggestion}</div>
          )}
          <div className="text-[10px] text-muted mt-1">
            Based on {p.sample_size} data points
          </div>
        </div>
      ))}
    </section>
  );
}
