import type { BlockRead } from "@/api/types";
import { categoryColor, fmtTime, minutesToLabel, STATUS_META } from "@/lib/format";

interface Props {
  block: BlockRead;
  top: number;
  height: number;
  onClick: () => void;
}

export default function BlockCard({ block, top, height, onClick }: Props) {
  const color = categoryColor(block.category);
  const status = STATUS_META[block.status];
  const hasLog = !!block.log;

  return (
    <button
      onClick={onClick}
      className="absolute left-12 right-2 overflow-hidden rounded-xl border border-white/5 px-3 py-1.5 text-left transition hover:brightness-110"
      style={{
        top: `${top}px`,
        height: `${Math.max(height, 28)}px`,
        background: `${color}18`,
        borderLeftWidth: "3px",
        borderLeftColor: color,
      }}
    >
      <div className="truncate text-xs font-semibold leading-tight">{block.title}</div>
      {height >= 44 && (
        <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-muted">
          <span>
            {fmtTime(block.start)}–{fmtTime(block.end)}
          </span>
          <span>·</span>
          <span>{minutesToLabel(block.planned_minutes)}</span>
        </div>
      )}
      {height >= 62 && hasLog && (
        <div className="mt-1 flex items-center gap-1.5">
          <span className={`pill text-[9px] ${status.cls}`}>{status.label}</span>
          {block.log!.actual_minutes != null && (
            <span className="text-[10px] text-muted">
              → {minutesToLabel(block.log!.actual_minutes)}
            </span>
          )}
        </div>
      )}
      {height >= 80 && hasLog && block.log!.what_happened && (
        <div className="mt-0.5 truncate text-[10px] italic text-muted">
          "{block.log!.what_happened}"
        </div>
      )}
    </button>
  );
}
