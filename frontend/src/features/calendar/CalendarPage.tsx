import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import type { BlockCreate, BlockRead, BlockUpdate } from "@/api/types";

import BlockModal from "./BlockModal";
import DateSwitcher from "./DateSwitcher";
import TimelineView from "./TimelineView";
import { useCalendarDay } from "./useCalendarDay";

export default function CalendarPage() {
  const qc = useQueryClient();
  const { date, dayStart, dayEnd, prev, next, today, isToday } = useCalendarDay();

  // NL planner state
  const [planText, setPlanText] = useState("");
  const [showPlanner, setShowPlanner] = useState(false);

  // Modal state
  const [modalBlock, setModalBlock] = useState<BlockRead | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [slotStart, setSlotStart] = useState<string | undefined>();
  const [slotEnd, setSlotEnd] = useState<string | undefined>();

  const blocks = useQuery({
    queryKey: ["blocks", date],
    queryFn: () => api.listBlocks(dayStart, dayEnd),
  });

  const plan = useMutation({
    mutationFn: (t: string) => api.planDay({ text: t, date }),
    onSuccess: () => {
      setPlanText("");
      qc.invalidateQueries({ queryKey: ["blocks"] });
      qc.invalidateQueries({ queryKey: ["summary"] });
    },
  });

  const createBlock = useMutation({
    mutationFn: (body: BlockCreate) => api.createBlock(body),
    onSuccess: () => {
      setModalOpen(false);
      qc.invalidateQueries({ queryKey: ["blocks"] });
    },
  });

  const updateBlock = useMutation({
    mutationFn: ({ id, body }: { id: number; body: BlockUpdate }) => api.updateBlock(id, body),
    onSuccess: () => {
      setModalOpen(false);
      qc.invalidateQueries({ queryKey: ["blocks"] });
    },
  });

  const deleteBlock = useMutation({
    mutationFn: (id: number) => api.deleteBlock(id),
    onSuccess: () => {
      setModalOpen(false);
      qc.invalidateQueries({ queryKey: ["blocks"] });
    },
  });

  const handleBlockClick = (block: BlockRead) => {
    setModalBlock(block);
    setSlotStart(undefined);
    setSlotEnd(undefined);
    setModalOpen(true);
  };

  const handleSlotClick = (startTime: string, endTime: string) => {
    setModalBlock(null);
    setSlotStart(startTime);
    setSlotEnd(endTime);
    setModalOpen(true);
  };

  const handleSave = (data: BlockCreate | BlockUpdate) => {
    if (modalBlock) {
      updateBlock.mutate({ id: modalBlock.id, body: data as BlockUpdate });
    } else {
      createBlock.mutate(data as BlockCreate);
    }
  };

  return (
    <div className="space-y-3">
      {/* Date navigation */}
      <DateSwitcher date={date} isToday={isToday} onPrev={prev} onNext={next} onToday={today} />

      {/* Plan with Bogi toggle */}
      <button
        className={`w-full text-left ${showPlanner ? "btn-brand" : "btn-ghost"} text-sm`}
        onClick={() => setShowPlanner(!showPlanner)}
      >
        ✎ Plan with Bogi
      </button>

      {/* NL Planner panel */}
      {showPlanner && (
        <section className="card p-4">
          <p className="mb-2 text-xs text-muted">
            Describe your day naturally — Bogi turns it into time blocks.
          </p>
          <textarea
            className="input min-h-[72px] resize-none text-sm"
            placeholder="e.g. record podcast 1hr, edit videos 2hrs, gym 45min…"
            value={planText}
            onChange={(e) => setPlanText(e.target.value)}
          />
          <button
            className="btn-brand mt-2 w-full text-sm"
            disabled={!planText.trim() || plan.isPending}
            onClick={() => plan.mutate(planText)}
          >
            {plan.isPending ? "Planning…" : "Turn into blocks"}
          </button>
          {plan.data && (
            <div className="mt-2 rounded-xl bg-brand/10 p-2.5 text-xs text-brand">
              {plan.data.message}
            </div>
          )}
        </section>
      )}

      {/* Timeline */}
      <section className="card overflow-hidden p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wide text-muted">Timeline</h3>
          <span className="text-[10px] text-muted">Tap slot to add</span>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: "520px" }}>
          <TimelineView
            blocks={blocks.data ?? []}
            date={date}
            onBlockClick={handleBlockClick}
            onSlotClick={handleSlotClick}
          />
        </div>
      </section>

      {/* Modal */}
      {modalOpen && (
        <BlockModal
          block={modalBlock}
          defaultStart={slotStart}
          defaultEnd={slotEnd}
          onSave={handleSave}
          onDelete={modalBlock ? () => deleteBlock.mutate(modalBlock.id) : undefined}
          onClose={() => setModalOpen(false)}
        />
      )}
    </div>
  );
}
