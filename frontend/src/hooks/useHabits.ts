"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "@/lib/api";
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
      if (completed) {
        // Remove completion
        await apiJson(`/api/v1/habits/${habitId}/log/${date}`, { method: "DELETE" });
      } else {
        // Add completion
        await apiJson(`/api/v1/habits/${habitId}/log`, {
          method: "POST",
          body: JSON.stringify({ completed_date: date }),
        });
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["habits"] });
    },
  });
}

export function useDeleteHabit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiJson(`/api/v1/habits/${id}`, { method: "DELETE" }).catch(() => null),
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
