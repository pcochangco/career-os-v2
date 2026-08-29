import { useRouter } from "expo-router";
import { useEffect, useState } from "react";

import { ErrorState, LoadingState } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Goal } from "@/lib/types";

function routeForGoal(goal: Goal): string {
  if (goal.active_roadmap_id) {
    return `/goals/${goal.id}/roadmap?roadmapId=${goal.active_roadmap_id}`;
  }
  if (goal.latest_draft_roadmap_id) {
    return `/goals/${goal.id}/review?roadmapId=${goal.latest_draft_roadmap_id}`;
  }
  return `/goals/${goal.id}/discovery`;
}

export default function IndexRoute() {
  const router = useRouter();
  const session = useSession();
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!session.ready || !session.token) return;
    let active = true;
    async function openNext() {
      try {
        setError(null);
        const goals = await apiRequest<Goal[]>("/goals", { token: session.token });
        if (!active) return;
        if (goals.length === 0) router.replace("/goals/new" as never);
        else if (goals.length === 1 && goals[0]) router.replace(routeForGoal(goals[0]) as never);
        else router.replace("/goals" as never);
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Your goals could not be loaded.");
      }
    }
    void openNext();
    return () => {
      active = false;
    };
  }, [attempt, router, session.ready, session.token]);

  if (session.error) return <ErrorState message={session.error} onRetry={session.retry} />;
  if (error) return <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />;
  return <LoadingState />;
}
