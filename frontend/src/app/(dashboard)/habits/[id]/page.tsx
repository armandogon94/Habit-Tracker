"use client";

import { useAnalytics, useCalendar, useHabit, useToggleHabit, useDeleteHabit } from "@/hooks/useHabits";
import { useAuth } from "@/lib/auth";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

function HeatmapGrid({ habitId, color }: { habitId: string; color: string }) {
  const { data: calendar } = useCalendar(habitId);

  const weeks = useMemo(() => {
    if (!calendar) return [];
    const result: { date: string; completed: boolean }[][] = [];
    let currentWeek: { date: string; completed: boolean }[] = [];

    for (const day of calendar) {
      const d = new Date(day.date + "T00:00:00");
      if (d.getDay() === 0 && currentWeek.length > 0) {
        result.push(currentWeek);
        currentWeek = [];
      }
      currentWeek.push(day);
    }
    if (currentWeek.length > 0) result.push(currentWeek);
    return result;
  }, [calendar]);

  if (!calendar) {
    return <div className="h-32 bg-slate-700 rounded-lg animate-pulse" />;
  }

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex gap-[3px] min-w-max">
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col gap-[3px]">
            {week.map((day) => (
              <div
                key={day.date}
                className="w-3 h-3 rounded-sm transition-colors"
                style={{
                  backgroundColor: day.completed ? color : "rgb(30 41 59)",
                  opacity: day.completed ? 1 : 0.3,
                }}
                title={`${day.date}: ${day.completed ? "Completed" : "Missed"}`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function HabitDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { user, loading: authLoading } = useAuth();
  const { data: habit, isLoading } = useHabit(id);
  const { data: analytics } = useAnalytics(id);
  const toggle = useToggleHabit();
  const deleteHabit = useDeleteHabit();

  useEffect(() => {
    if (!authLoading && !user) router.replace("/login");
  }, [user, authLoading, router]);

  if (authLoading || !user || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-slate-400">Loading...</div>
      </div>
    );
  }

  if (!habit) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <p className="text-slate-400">Habit not found</p>
        <Link href="/habits" className="text-blue-400 hover:text-blue-300">
          Back to habits
        </Link>
      </div>
    );
  }

  const today = new Date().toISOString().split("T")[0];

  const weeklyData = analytics
    ? Object.entries(analytics.weekly_counts).map(([day, count]) => ({
        day,
        count,
      }))
    : [];

  async function handleDelete() {
    if (!confirm("Archive this habit? You can't undo this.")) return;
    await deleteHabit.mutateAsync(id);
    router.push("/habits");
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
          <Link
            href="/habits"
            className="text-slate-400 hover:text-white transition"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold truncate">{habit.name}</h1>
          </div>
          <button
            onClick={handleDelete}
            className="text-sm text-red-400 hover:text-red-300 transition px-3 py-1.5 rounded-lg hover:bg-red-500/10"
          >
            Archive
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Today toggle */}
        <div
          className="bg-slate-800 rounded-xl p-6 flex items-center justify-between"
          style={{ borderLeft: `4px solid ${habit.color}` }}
        >
          <div>
            <p className="text-slate-400 text-sm">Today</p>
            <p className="text-lg font-semibold mt-0.5">
              {habit.completed_today ? "Completed" : "Not yet"}
            </p>
          </div>
          <button
            onClick={() =>
              toggle.mutate({
                habitId: habit.id,
                date: today,
                completed: habit.completed_today,
              })
            }
            disabled={toggle.isPending}
            className={`w-14 h-14 rounded-full flex items-center justify-center transition-all text-xl ${
              habit.completed_today
                ? "bg-green-500 text-white hover:bg-green-600"
                : "bg-slate-700 text-slate-400 hover:bg-slate-600"
            }`}
          >
            {habit.completed_today ? "\u2713" : "\u25CB"}
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Current Streak", value: habit.current_streak, unit: "days", accent: "text-orange-400" },
            { label: "Longest Streak", value: habit.longest_streak, unit: "days", accent: "text-blue-400" },
            { label: "Completions", value: analytics?.total_completions ?? 0, unit: "total", accent: "text-green-400" },
            { label: "Rate (30d)", value: `${analytics?.completion_rate ?? 0}%`, unit: "", accent: "text-purple-400" },
          ].map((stat) => (
            <div key={stat.label} className="bg-slate-800 rounded-xl p-4 text-center">
              <p className="text-slate-400 text-xs mb-1">{stat.label}</p>
              <p className={`text-2xl font-bold ${stat.accent}`}>{stat.value}</p>
              {stat.unit && <p className="text-slate-500 text-xs">{stat.unit}</p>}
            </div>
          ))}
        </div>

        {/* Heatmap */}
        <div className="bg-slate-800 rounded-xl p-6">
          <h2 className="font-semibold mb-4">Completion History (1 Year)</h2>
          <HeatmapGrid habitId={habit.id} color={habit.color} />
        </div>

        {/* Weekly distribution chart */}
        {weeklyData.length > 0 && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h2 className="font-semibold mb-4">Weekly Distribution</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="day" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    color: "#f1f5f9",
                  }}
                />
                <Bar dataKey="count" fill={habit.color} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            {analytics?.best_day && (
              <p className="text-sm text-slate-400 mt-3">
                Best day: <span className="text-white font-medium">{analytics.best_day}</span>
              </p>
            )}
          </div>
        )}

        {/* Description */}
        {habit.description && (
          <div className="bg-slate-800 rounded-xl p-6">
            <h2 className="font-semibold mb-2">Description</h2>
            <p className="text-slate-400">{habit.description}</p>
          </div>
        )}
      </main>
    </div>
  );
}
