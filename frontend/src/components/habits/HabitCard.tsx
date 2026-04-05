"use client";

import { useToggleHabit } from "@/hooks/useHabits";
import type { Habit } from "@/types/habit";
import Link from "next/link";

export function HabitCard({ habit }: { habit: Habit }) {
  const toggle = useToggleHabit();
  const today = new Date().toISOString().split("T")[0];

  function handleToggle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    toggle.mutate({
      habitId: habit.id,
      date: today,
      completed: habit.completed_today,
    });
  }

  return (
    <Link href={`/habits/${habit.id}`}>
      <div
        className="bg-slate-800 rounded-xl p-5 shadow-lg hover:shadow-xl hover:bg-slate-750 transition-all cursor-pointer group"
        style={{ borderLeft: `4px solid ${habit.color}` }}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-lg truncate group-hover:text-white transition">
              {habit.name}
            </h3>
            {habit.description && (
              <p className="text-slate-400 text-sm mt-0.5 truncate">
                {habit.description}
              </p>
            )}
          </div>

          <button
            onClick={handleToggle}
            disabled={toggle.isPending}
            className={`ml-3 w-10 h-10 rounded-full flex items-center justify-center transition-all shrink-0 ${
              habit.completed_today
                ? "bg-green-500 text-white hover:bg-green-600"
                : "bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-white"
            }`}
            aria-label={habit.completed_today ? "Undo completion" : "Mark complete"}
          >
            {habit.completed_today ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" strokeWidth={2} />
              </svg>
            )}
          </button>
        </div>

        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <span className="text-orange-400 text-lg font-bold">{habit.current_streak}</span>
            <span className="text-slate-400">day streak</span>
          </div>
          <div className="text-slate-500">|</div>
          <div className="flex items-center gap-1.5">
            <span className="text-slate-300 font-medium">{habit.longest_streak}</span>
            <span className="text-slate-500">best</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
