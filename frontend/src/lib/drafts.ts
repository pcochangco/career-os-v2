/**
 * Small, best-effort store for text a user has typed but not yet saved, so a refresh, the back
 * button, or a brief navigation never loses it. Web uses localStorage (per device, cleared when
 * the draft is submitted); native keeps drafts in memory for the app session.
 */
const memory = new Map<string, string>();
const PREFIX = "careeros.draft.";

function storage(): Storage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

export function readDraft(key: string): string | null {
  try {
    return storage()?.getItem(PREFIX + key) ?? memory.get(key) ?? null;
  } catch {
    return memory.get(key) ?? null;
  }
}

export function writeDraft(key: string, value: string): void {
  if (!value) {
    clearDraft(key);
    return;
  }
  memory.set(key, value);
  try {
    storage()?.setItem(PREFIX + key, value);
  } catch {
    // Storage can be full or blocked (private mode); the in-memory copy still helps.
  }
}

export function clearDraft(key: string): void {
  memory.delete(key);
  try {
    storage()?.removeItem(PREFIX + key);
  } catch {
    // Ignore: nothing to clean up.
  }
}
