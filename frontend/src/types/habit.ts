export interface Habit {
  id: string;
  name: string;
  description: string | null;
  color: string;
  rrule: string;
  created_at: string;
  archived_at: string | null;
  current_streak: number;
  longest_streak: number;
  completed_today: boolean;
}

export interface HabitLog {
  id: string;
  habit_id: string;
  completed_date: string;
  notes: string | null;
  created_at: string;
}

export interface CalendarDay {
  date: string;
  completed: boolean;
}

export interface HabitAnalytics {
  total_completions: number;
  completion_rate: number;
  current_streak: number;
  longest_streak: number;
  best_day: string | null;
  weekly_counts: Record<string, number>;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  timezone: string;
}
