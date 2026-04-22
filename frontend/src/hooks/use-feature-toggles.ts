import { useSyncExternalStore } from 'react';

const STORAGE_KEY = 'feature-toggles';

export type FeatureToggles = {
  sakura: boolean;
  live2d: boolean;
};

const defaults: FeatureToggles = {
  sakura: false,
  live2d: false,
};

function readFromStorage(): FeatureToggles {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw);
    return { ...defaults, ...parsed };
  } catch {
    return defaults;
  }
}

let current: FeatureToggles = readFromStorage();
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function getFeatureToggles(): FeatureToggles {
  return current;
}

export function setFeatureToggle<K extends keyof FeatureToggles>(key: K, value: FeatureToggles[K]) {
  if (current[key] === value) return;
  current = { ...current, [key]: value };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
  } catch {
    // ignore quota errors
  }
  notify();
}

export function useFeatureToggles(): FeatureToggles {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => {
        listeners.delete(cb);
      };
    },
    () => current,
    () => defaults,
  );
}
