import { useEffect, useState } from "react";

import type { BlockCreate, BlockRead, BlockUpdate } from "@/api/types";
import { STATUS_META } from "@/lib/format";

interface Props {
  block: BlockRead | null;
  defaultStart?: string;
  defaultEnd?: string;
  onSave: (data: BlockCreate | BlockUpdate) => void;
  onDelete?: () => void;
  onClose: () => void;
}

const CATEGORIES = ["Work", "Study", "Health", "Social", "Chores", "Rest", "Social media"];

export default function BlockModal({ block, defaultStart, defaultEnd, onSave, onDelete, onClose }: Props) {
  const isEdit = !!block;

  const [title, setTitle] = useState(block?.title ?? "");
  const [category, setCategory] = useState(block?.category ?? "Work");
  const [start, setStart] = useState(block?.start?.slice(11, 16) ?? defaultStart?.slice(11, 16) ?? "09:00");
  const [end, setEnd] = useState(block?.end?.slice(11, 16) ?? defaultEnd?.slice(11, 16) ?? "10:00");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    if (isEdit) {
      const data: BlockUpdate = { title, category, start: toISO(start), end: toISO(end) };
      onSave(data);
    } else {
      const data: BlockCreate = { title, category, start: toISO(start), end: toISO(end) };
      onSave(data);
    }
  };

  const toISO = (time: string) => {
    const datePrefix = block?.start?.slice(0, 10) ?? (defaultStart && defaultStart.length >= 10 ? defaultStart.slice(0, 10) : new Date().toISOString().slice(0, 10));
    return `${datePrefix}T${time}:00`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="card mx-4 mb-4 w-full max-w-md p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-bold">{isEdit ? "Edit Block" : "New Block"}</h3>
          <button className="text-muted hover:text-white" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            className="input"
            placeholder="What are you planning?"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoFocus
          />

          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                className={`pill transition ${category === c ? "bg-brand text-white" : "bg-white/5 text-muted hover:text-white"}`}
                onClick={() => setCategory(c)}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="time"
              className="input flex-1 text-center"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
            <span className="text-muted">→</span>
            <input
              type="time"
              className="input flex-1 text-center"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>

          {isEdit && block?.log && (
            <div className="rounded-xl bg-panel2 p-3">
              <div className="mb-1 flex items-center gap-2">
                <span className={`pill text-[10px] ${STATUS_META[block.status].cls}`}>
                  {STATUS_META[block.status].label}
                </span>
                <span className="text-xs text-muted">Reality</span>
              </div>
              <p className="text-xs italic text-muted">"{block.log.what_happened}"</p>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            {isEdit && onDelete && (
              <button
                type="button"
                className="btn-ghost flex-1 text-bad"
                onClick={onDelete}
              >
                Delete
              </button>
            )}
            <button
              type="submit"
              className="btn-brand flex-1"
              disabled={!title.trim()}
            >
              {isEdit ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
