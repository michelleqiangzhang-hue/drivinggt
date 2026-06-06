interface Props {
  date: string;
  isToday: boolean;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
}

export default function DateSwitcher({ date, isToday, onPrev, onNext, onToday }: Props) {
  const d = new Date(date + "T00:00:00");
  const label = d.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });

  return (
    <div className="flex items-center justify-between">
      <button className="btn-ghost px-3 py-1 text-sm" onClick={onPrev}>
        ‹
      </button>
      <div className="flex items-center gap-2">
        <span className="text-sm font-bold">{label}</span>
        {!isToday && (
          <button className="pill bg-brand/20 text-brand text-[10px]" onClick={onToday}>
            Today
          </button>
        )}
      </div>
      <button className="btn-ghost px-3 py-1 text-sm" onClick={onNext}>
        ›
      </button>
    </div>
  );
}
