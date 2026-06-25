"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiJson } from "@/lib/api";
import type { CalendarDay, Habit, HabitAnalytics } from "@/types/habit";

export function useHabits() {
  return useQuery<Habit[]>({
    queryKey: ["habits"],
    queryFn: () => apiJson("/api/v1/habits"),
  });
}

export function useHabit(id: string) {
  return useQuery<Habit>({
    queryKey: ["habit", id],
    queryFn: () => apiJson(`/api/v1/habits/${id}`),
    enabled: !!id,
  });
}

export function useCreateHabit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; description?: string; color?: string; rrule?: string }) =>
      apiJson("/api/v1/habits", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["habits"] }),
  });
}

export function useToggleHabit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      habitId,
      date,
      completed,
    }: {
      habitId: string;
      date: string;
      completed: boolean;
    }) => {
      const res = completed
        ? await apiFetch(`/api/v1/habits/${habitId}/log/${date}`, { method: "DELETE" })
        : await apiFetch(`/api/v1/habits/${habitId}/log`, {
            method: "POST",
            body: JSON.stringify({ completed_date: date }),
          });
      // Idempotent: completing an already-completed day (409) or un-completing a
      // day that has no log (404) already satisfy the intended end state, so a
      // double/cross-component tap converges instead of surfacing an error.
      if (!res.ok && res.status !== 404 && res.status !== 409) {
        const err = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
    },
    // Optimistic flip so the toggle responds instantly and a second tap reads
    // fresh state instead of re-firing against the old value.
    onMutate: async ({ habitId, completed }) => {
      await qc.cancelQueries({ queryKey: ["habits"] });
      await qc.cancelQueries({ queryKey: ["habit", habitId] });
      const prevList = qc.getQueryData<Habit[]>(["habits"]);
      const prevHabit = qc.getQueryData<Habit>(["habit", habitId]);
      qc.setQueryData<Habit[]>(["habits"], (old) =>
        old?.map((h) => (h.id === habitId ? { ...h, completed_today: !completed } : h)),
      );
      qc.setQueryData<Habit>(["habit", habitId], (h) =>
        h ? { ...h, completed_today: !completed } : h,
      );
      return { prevList, prevHabit };
    },
    onError: (_err, { habitId }, ctx) => {
      if (ctx?.prevList) qc.setQueryData(["habits"], ctx.prevList);
      if (ctx?.prevHabit) qc.setQueryData(["habit", habitId], ctx.prevHabit);
    },
    // Refetch every key the list AND the detail page depend on. The old code
    // only invalidated ["habits"], leaving the detail page's habit/analytics/
    // calendar caches stale after a toggle.
    onSettled: (_data, _err, { habitId }) => {
      qc.invalidateQueries({ queryKey: ["habits"] });
      qc.invalidateQueries({ queryKey: ["habit", habitId] });
      qc.invalidateQueries({ queryKey: ["analytics", habitId] });
      qc.invalidateQueries({ queryKey: ["calendar", habitId] });
    },
  });
}

export function useDeleteHabit() {
  const qc = useQueryClient();
  return useMutation({
    // No error swallowing: a failed archive must reject so the caller doesn't
    // navigate away as if it succeeded. apiJson handles the 204 (no body).
    mutationFn: (id: string) => apiJson(`/api/v1/habits/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["habits"] }),
  });
}

export function useCalendar(habitId: string) {
  return useQuery<CalendarDay[]>({
    queryKey: ["calendar", habitId],
    queryFn: () => apiJson(`/api/v1/habits/${habitId}/calendar`),
    enabled: !!habitId,
  });
}

export function useAnalytics(habitId: string) {
  return useQuery<HabitAnalytics>({
    queryKey: ["analytics", habitId],
    queryFn: () => apiJson(`/api/v1/habits/${habitId}/analytics`),
    enabled: !!habitId,
  });
}
