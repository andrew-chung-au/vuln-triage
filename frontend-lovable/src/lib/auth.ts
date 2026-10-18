import { useSyncExternalStore } from "react";
import type { User } from "@/services/types";

const KEY = "vulntriage-user";
let current: User | null = null;
let loaded = false;
const listeners = new Set<() => void>();

function load() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  try {
    const raw = window.sessionStorage.getItem(KEY);
    current = raw ? (JSON.parse(raw) as User) : null;
  } catch {
    current = null;
  }
}

export function setUser(user: User | null) {
  current = user;
  loaded = true;
  if (typeof window !== "undefined") {
    if (user) window.sessionStorage.setItem(KEY, JSON.stringify(user));
    else window.sessionStorage.removeItem(KEY);
  }
  listeners.forEach((l) => l());
}

export function getUser() {
  load();
  return current;
}

/** Returns undefined during SSR / before hydration, otherwise the user or null. */
export function useUser(): User | null | undefined {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => getUser(),
    () => undefined,
  );
}
