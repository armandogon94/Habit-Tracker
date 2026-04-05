"use client";

import { HabitCard } from "@/components/habits/HabitCard";
import { CreateHabitModal } from "@/components/habits/CreateHabitModal";
import { useHabits } from "@/hooks/useHabits";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function HabitsPage() {
  const { user, loading: authLoading, logout } = useAuth();
  const router = useRouter();
  const { data: habits, isLoading, error } = useHabits();
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [user, authLoading, router]);

  if (authLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-slate-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">My Habits</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400 hidden sm:block">{user.email}</span>
            <button
              onClick={logout}
              className="text-sm text-slate-400 hover:text-white transition px-3 py-1.5 rounded-lg hover:bg-slate-800"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {/* Stats bar */}
        {habits && habits.length > 0 && (
          <div className="flex items-center gap-6 mb-8 text-sm">
            <div className="bg-slate-800 rounded-lg px-4 py-3">
              <span className="text-slate-400">Total:</span>{" "}
              <span className="font-bold text-white">{habits.length}</span>
            </div>
            <div className="bg-slate-800 rounded-lg px-4 py-3">
              <span className="text-slate-400">Done today:</span>{" "}
              <span className="font-bold text-green-400">
                {habits.filter((h) => h.completed_today).length}
              </span>
              <span className="text-slate-500"> / {habits.length}</span>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6">
            Failed to load habits. Please try again.
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="bg-slate-800 rounded-xl p-5 animate-pulse h-32" />
            ))}
          </div>
        )}

        {/* Habit cards */}
        {habits && habits.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {habits.map((habit) => (
              <HabitCard key={habit.id} habit={habit} />
            ))}
          </div>
        )}

        {/* Empty state */}
        {habits && habits.length === 0 && (
          <div className="text-center py-16">
            <div className="text-5xl mb-4">&#127919;</div>
            <h2 className="text-xl font-semibold mb-2">No habits yet</h2>
            <p className="text-slate-400 mb-6">
              Create your first habit to start building consistency.
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-6 rounded-lg transition"
            >
              Create Your First Habit
            </button>
          </div>
        )}

        {/* FAB */}
        {habits && habits.length > 0 && (
          <button
            onClick={() => setShowModal(true)}
            className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white w-14 h-14 rounded-full shadow-lg hover:shadow-xl transition-all flex items-center justify-center text-2xl"
            aria-label="Create new habit"
          >
            +
          </button>
        )}

        {showModal && <CreateHabitModal onClose={() => setShowModal(false)} />}
      </main>
    </div>
  );
}
