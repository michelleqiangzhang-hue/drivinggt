import type { BlockRead } from "@/api/types";
import BlockCard from "./BlockCard";

const START_HOUR = 6;
const END_HOUR = 24;
const HOUR_HEIGHT = 60; // px per hour

interface Props {
  blocks: BlockRead[];
  date: string;
  onBlockClick: (block: BlockRead) => void;
  onSlotClick: (startTime: string, endTime: string) => void;
}

function hourToMinutes(hour: number): number {
  return hour * 60;
}

function timeToPosition(iso: string): number {
  const d = new Date(iso);
  const minutes = d.getHours() * 60 + d.getMinutes();
  const offsetFromStart = minutes - hourToMinutes(START_HOUR);
  return (offsetFromStart / 60) * HOUR_HEIGHT;
}

function durationToHeight(startIso: string, endIso: string): number {
  const startMs = new Date(startIso).getTime();
  const endMs = new Date(endIso).getTime();
  const diffMinutes = (endMs - startMs) / 60000;
  return (diffMinutes / 60) * HOUR_HEIGHT;
}

export default function TimelineView({ blocks, date, onBlockClick, onSlotClick }: Props) {
  const hours = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);
  const totalHeight = hours.length * HOUR_HEIGHT;

  const handleSlotClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const minutesFromStart = (y / totalHeight) * (END_HOUR - START_HOUR) * 60;
    const totalMinutes = hourToMinutes(START_HOUR) + minutesFromStart;
    const startHour = Math.floor(totalMinutes / 60);
    const startMin = Math.round(totalMinutes % 60 / 15) * 15;

    const pad = (n: number) => String(n).padStart(2, "0");
    const startTime = `${pad(startHour)}:${pad(startMin % 60)}`;
    const endTotalMin = startHour * 60 + startMin + 60;
    const endTime = `${pad(Math.min(Math.floor(endTotalMin / 60), 23))}:${pad(endTotalMin % 60)}`;

    onSlotClick(`${date}T${startTime}:00`, `${date}T${endTime}:00`);
  };

  // Filter blocks to show only those within timeline range
  const visibleBlocks = blocks.filter((b) => {
    const bStart = new Date(b.start);
    const bHour = bStart.getHours() + bStart.getMinutes() / 60;
    return bHour >= START_HOUR && bHour < END_HOUR;
  });

  return (
    <div
      className="relative select-none"
      style={{ height: `${totalHeight}px` }}
      onClick={handleSlotClick}
    >
      {/* Hour gridlines */}
      {hours.map((h) => (
        <div
          key={h}
          className="absolute left-0 right-0 border-t border-white/5"
          style={{ top: `${(h - START_HOUR) * HOUR_HEIGHT}px` }}
        >
          <span className="absolute -top-2 left-0 text-[10px] font-medium text-muted">
            {h}:00
          </span>
        </div>
      ))}

      {/* Now indicator */}
      <NowIndicator date={date} />

      {/* Blocks */}
      {visibleBlocks.map((block) => (
        <BlockCard
          key={block.id}
          block={block}
          top={timeToPosition(block.start)}
          height={durationToHeight(block.start, block.end)}
          onClick={() => onBlockClick(block)}
        />
      ))}
    </div>
  );
}

function NowIndicator({ date }: { date: string }) {
  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  if (date !== todayStr) return null;

  const minutes = now.getHours() * 60 + now.getMinutes();
  const offset = minutes - hourToMinutes(START_HOUR);
  if (offset < 0 || offset > (END_HOUR - START_HOUR) * 60) return null;

  const top = (offset / 60) * HOUR_HEIGHT;

  return (
    <div className="absolute left-10 right-0 z-10 flex items-center" style={{ top: `${top}px` }}>
      <div className="h-2 w-2 rounded-full bg-brand" />
      <div className="h-px flex-1 bg-brand" />
    </div>
  );
}
