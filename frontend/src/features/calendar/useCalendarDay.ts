import { useState } from "react";

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function useCalendarDay() {
  const [date, setDate] = useState(() => toDateStr(new Date()));

  const prev = () => {
    const d = new Date(date + "T00:00:00");
    d.setDate(d.getDate() - 1);
    setDate(toDateStr(d));
  };

  const next = () => {
    const d = new Date(date + "T00:00:00");
    d.setDate(d.getDate() + 1);
    setDate(toDateStr(d));
  };

  const today = () => setDate(toDateStr(new Date()));

  const isToday = date === toDateStr(new Date());

  const dayStart = `${date}T00:00:00`;
  const dayEnd = `${date}T23:59:59`;

  return { date, dayStart, dayEnd, prev, next, today, isToday };
}
