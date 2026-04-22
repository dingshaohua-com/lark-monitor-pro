import { useSyncExternalStore } from 'react';
import { ENV_PRIMARY } from '@/config/theme';

const STORAGE_KEY = 'theme-primary';

function readFromStorage(): string {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw && typeof raw === 'string') return raw;
  } catch {
    // ignore
  }
  return ENV_PRIMARY;
}

let current: string = readFromStorage();
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function getThemePrimary(): string {
  return current;
}

export function setThemePrimary(color: string) {
  if (current === color) return;
  current = color;
  try {
    localStorage.setItem(STORAGE_KEY, color);
  } catch {
    // ignore quota errors
  }
  notify();
}

export function useThemePrimary(): string {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => {
        listeners.delete(cb);
      };
    },
    () => current,
    () => ENV_PRIMARY,
  );
}
