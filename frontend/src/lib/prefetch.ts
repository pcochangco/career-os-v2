import { apiRequest } from "@/lib/api";
import { Goal } from "@/lib/types";

/**
 * Start loading the goal list while the account check is still in flight, so a returning user
 * doesn't wait for two requests one after the other. Whichever screen needs goals first takes the
 * in-flight request; anything later fetches fresh.
 */
let pending: { token: string; request: Promise<Goal[]>; startedAt: number } | null = null;
// Only startup should use the prefetch. A deep link that never shows the goal list mustn't leave a
// stale copy behind for a later visit (after, say, creating a goal).
const SHELF_LIFE_MS = 10_000;

export function prefetchGoals(token: string): void {
  const request = apiRequest<Goal[]>("/goals", { token });
  // Errors surface to whoever takes the request; never leave an unhandled rejection behind.
  request.catch(() => undefined);
  pending = { token, request, startedAt: Date.now() };
}

export function loadGoals(token: string): Promise<Goal[]> {
  const prefetched = pending;
  pending = null;
  if (prefetched?.token === token && Date.now() - prefetched.startedAt < SHELF_LIFE_MS) {
    return prefetched.request;
  }
  return apiRequest<Goal[]>("/goals", { token });
}

export function clearPrefetchedGoals(): void {
  pending = null;
}
