import * as SecureStore from "expo-secure-store";
import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { Platform } from "react-native";

import { ApiError, apiRequest } from "@/lib/api";

export type IdentityProvider = "apple" | "google";

export type Account = {
  email: string;
  provider_config: {
    apple: boolean;
    google: boolean;
    google_android_client_id: string;
    google_ios_client_id: string;
    google_web_client_id: string;
  };
  providers: IdentityProvider[];
  status: "guest" | "saved";
  user_id: string;
};

type SessionResponse = {
  access_token: string;
  token_type: "bearer";
  user_id: string;
};

type SessionContextValue = {
  account: Account | null;
  accountLoading: boolean;
  deleteAccount: () => Promise<void>;
  error: string | null;
  linkIdentity: (provider: IdentityProvider, identityToken: string) => Promise<void>;
  ready: boolean;
  retry: () => void;
  signOut: () => Promise<void>;
  token: string | null;
};

const TOKEN_KEY = "careeros.session";
const SessionContext = createContext<SessionContextValue | null>(null);

async function readStoredToken(): Promise<string | null> {
  if (Platform.OS === "web" && typeof localStorage !== "undefined") {
    return localStorage.getItem(TOKEN_KEY);
  }
  return SecureStore.getItemAsync(TOKEN_KEY);
}

async function storeToken(token: string): Promise<void> {
  if (Platform.OS === "web" && typeof localStorage !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
    return;
  }
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

async function removeStoredToken(): Promise<void> {
  if (Platform.OS === "web" && typeof localStorage !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    return;
  }
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

async function createGuestSession(): Promise<SessionResponse> {
  return apiRequest<SessionResponse>("/auth/anonymous", { method: "POST" });
}

async function readAccount(token: string): Promise<Account> {
  return apiRequest<Account>("/auth/account", { token });
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [accountLoading, setAccountLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const activateSession = useCallback(async (session: SessionResponse) => {
    await storeToken(session.access_token);
    const nextAccount = await readAccount(session.access_token);
    setToken(session.access_token);
    setAccount(nextAccount);
  }, []);

  useEffect(() => {
    let active = true;
    async function initialize() {
      try {
        setError(null);
        setAccountLoading(true);
        const stored = await readStoredToken();
        if (stored) {
          try {
            const storedAccount = await readAccount(stored);
            if (active) {
              setToken(stored);
              setAccount(storedAccount);
              setAccountLoading(false);
            }
            return;
          } catch (caught) {
            if (!(caught instanceof ApiError) || caught.status !== 401) throw caught;
            await removeStoredToken();
          }
        }
        const session = await createGuestSession();
        await storeToken(session.access_token);
        const guestAccount = await readAccount(session.access_token);
        if (active) {
          setToken(session.access_token);
          setAccount(guestAccount);
          setAccountLoading(false);
        }
      } catch (caught) {
        if (active) {
          setAccountLoading(false);
          setError(caught instanceof Error ? caught.message : "CareerOS could not start.");
        }
      }
    }
    void initialize();
    return () => {
      active = false;
    };
  }, [attempt]);

  const linkIdentity = useCallback(
    async (provider: IdentityProvider, identityToken: string) => {
      if (!token) throw new Error("CareerOS is still opening. Please try again.");
      setAccountLoading(true);
      try {
        const session = await apiRequest<SessionResponse>(`/auth/link/${provider}`, {
          body: { identity_token: identityToken },
          method: "POST",
          token,
        });
        await activateSession(session);
      } finally {
        setAccountLoading(false);
      }
    },
    [activateSession, token],
  );

  const beginFreshGuestSession = useCallback(async () => {
    await removeStoredToken();
    setToken(null);
    setAccount(null);
    const session = await createGuestSession();
    await activateSession(session);
  }, [activateSession]);

  const signOut = useCallback(async () => {
    if (!token) return;
    setAccountLoading(true);
    try {
      await apiRequest<void>("/auth/logout", { method: "POST", token });
      await beginFreshGuestSession();
    } finally {
      setAccountLoading(false);
    }
  }, [beginFreshGuestSession, token]);

  const deleteAccount = useCallback(async () => {
    if (!token) return;
    setAccountLoading(true);
    try {
      await apiRequest<void>("/auth/account", { method: "DELETE", token });
      await beginFreshGuestSession();
    } finally {
      setAccountLoading(false);
    }
  }, [beginFreshGuestSession, token]);

  const value = useMemo(
    () => ({
      account,
      accountLoading,
      deleteAccount,
      error,
      linkIdentity,
      ready: token !== null,
      retry: () => setAttempt((value) => value + 1),
      signOut,
      token,
    }),
    [account, accountLoading, deleteAccount, error, linkIdentity, signOut, token],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider");
  return context;
}
