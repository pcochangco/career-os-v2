import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { Platform } from "react-native";

import { apiRequest } from "@/lib/api";

type SessionResponse = {
  access_token: string;
  token_type: "bearer";
  user_id: string;
};

type SessionContextValue = {
  error: string | null;
  ready: boolean;
  retry: () => void;
  token: string | null;
};

const TOKEN_KEY = "careeros.session";
const SessionContext = createContext<SessionContextValue | null>(null);
let nativeSessionToken: string | null = null;

function readStoredToken(): string | null {
  if (Platform.OS === "web" && typeof localStorage !== "undefined") {
    return localStorage.getItem(TOKEN_KEY);
  }
  return nativeSessionToken;
}

function storeToken(token: string): void {
  if (Platform.OS === "web" && typeof localStorage !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    nativeSessionToken = token;
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    async function initialize() {
      try {
        setError(null);
        const stored = readStoredToken();
        if (stored) {
          if (active) setToken(stored);
          return;
        }
        const session = await apiRequest<SessionResponse>("/auth/anonymous", { method: "POST" });
        storeToken(session.access_token);
        if (active) setToken(session.access_token);
      } catch (caught) {
        if (active) {
          setError(caught instanceof Error ? caught.message : "CareerOS could not start.");
        }
      }
    }
    void initialize();
    return () => {
      active = false;
    };
  }, [attempt]);

  const value = useMemo(
    () => ({ error, ready: token !== null, retry: () => setAttempt((value) => value + 1), token }),
    [error, token],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider");
  return context;
}
