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

import { ApiError, apiRequest, SESSION_ENDED_MESSAGE, setUnauthorizedHandler } from "@/lib/api";
import { clearPrefetchedGoals, prefetchGoals } from "@/lib/prefetch";

export type IdentityProvider = "apple" | "google" | "email";

export type ProviderConfig = {
  apple: boolean;
  email_test: boolean;
  google: boolean;
  google_android_client_id: string;
  google_ios_client_id: string;
  google_web_client_id: string;
};

export type Account = {
  email: string;
  /** Total goals the plan allows; null means unlimited (Premium). */
  goal_limit: number | null;
  plan: "free" | "premium";
  provider_config: ProviderConfig;
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
  clearNotice: () => void;
  deleteAccount: () => Promise<void>;
  error: string | null;
  linkIdentity: (provider: IdentityProvider, identityToken: string) => Promise<void>;
  /** A one-time message for the sign-in screen, such as "Your session has ended". */
  notice: string | null;
  providerConfig: ProviderConfig;
  ready: boolean;
  retry: () => void;
  signIn: (provider: IdentityProvider, identityToken: string) => Promise<string>;
  signInWithEmailTestAccess: (email: string, accessCode: string) => Promise<string>;
  signOut: () => Promise<void>;
  token: string | null;
};

const EMPTY_PROVIDER_CONFIG: ProviderConfig = {
  apple: false,
  email_test: false,
  google: false,
  google_android_client_id: "",
  google_ios_client_id: "",
  google_web_client_id: "",
};
const TOKEN_KEY = "careeros.session";
// Held outside React state: leaving the signed-in shell remounts the root layout, which would
// otherwise drop the message before the sign-in screen can show it.
let pendingNotice: string | null = null;
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

async function readAccount(token: string): Promise<Account> {
  return apiRequest<Account>("/auth/account", { token });
}

export function SessionProvider({
  children,
  enabled = true,
}: {
  children: ReactNode;
  enabled?: boolean;
}) {
  const [token, setToken] = useState<string | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [providerConfig, setProviderConfig] = useState(EMPTY_PROVIDER_CONFIG);
  const [accountLoading, setAccountLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [notice, setNoticeState] = useState<string | null>(() => pendingNotice);
  const setNotice = useCallback((next: string | null) => {
    pendingNotice = next;
    setNoticeState(next);
  }, []);

  const clearSession = useCallback(async () => {
    await removeStoredToken().catch(() => undefined);
    setToken(null);
    setAccount(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setNotice(SESSION_ENDED_MESSAGE);
      void clearSession();
    });
    return () => setUnauthorizedHandler(null);
  }, [clearSession, setNotice]);

  const activateSession = useCallback(async (session: SessionResponse): Promise<string> => {
    const nextAccount = await readAccount(session.access_token);
    if (nextAccount.status !== "saved") {
      throw new Error("A saved account is required to use CareerOS.");
    }
    await storeToken(session.access_token);
    setNotice(null);
    setToken(session.access_token);
    setAccount(nextAccount);
    setProviderConfig(nextAccount.provider_config);
    return session.access_token;
  }, [setNotice]);

  useEffect(() => {
    if (!enabled) {
      setReady(true);
      setAccountLoading(false);
      return;
    }
    let active = true;
    async function initialize() {
      try {
        setError(null);
        setReady(false);
        setAccountLoading(true);
        // A returning user's account already carries the sign-in config, and their goal list can
        // load alongside it: one round trip before the first screen instead of three in a row.
        const stored = await readStoredToken();
        let signedIn = false;
        if (stored) {
          prefetchGoals(stored);
          try {
            const storedAccount = await readAccount(stored);
            if (storedAccount.status === "saved") {
              signedIn = true;
              if (active) {
                setToken(stored);
                setAccount(storedAccount);
                setProviderConfig(storedAccount.provider_config);
              }
            } else {
              clearPrefetchedGoals();
              await removeStoredToken();
            }
          } catch (caught) {
            clearPrefetchedGoals();
            if (!(caught instanceof ApiError) || caught.status !== 401) throw caught;
            await removeStoredToken();
          }
        }
        if (!signedIn) {
          const config = await apiRequest<ProviderConfig>("/auth/config");
          if (active) setProviderConfig(config);
        }
      } catch (caught) {
        if (active) {
          setError(caught instanceof Error ? caught.message : "CareerOS could not start.");
        }
      } finally {
        if (active) {
          setReady(true);
          setAccountLoading(false);
        }
      }
    }
    void initialize();
    return () => {
      active = false;
    };
  }, [attempt, enabled]);

  const signIn = useCallback(
    async (provider: IdentityProvider, identityToken: string): Promise<string> => {
      setAccountLoading(true);
      try {
        const session = await apiRequest<SessionResponse>(`/auth/sign-in/${provider}`, {
          body: { identity_token: identityToken },
          method: "POST",
        });
        return await activateSession(session);
      } finally {
        setAccountLoading(false);
      }
    },
    [activateSession],
  );

  const signInWithEmailTestAccess = useCallback(
    async (email: string, accessCode: string): Promise<string> => {
      setAccountLoading(true);
      try {
        const session = await apiRequest<SessionResponse>("/auth/email-test-sign-in", {
          body: { access_code: accessCode, email },
          method: "POST",
        });
        return await activateSession(session);
      } finally {
        setAccountLoading(false);
      }
    },
    [activateSession],
  );

  const linkIdentity = useCallback(
    async (provider: IdentityProvider, identityToken: string) => {
      if (!token) throw new Error("Sign in before linking another provider.");
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

  const signOut = useCallback(async () => {
    if (!token) return;
    setAccountLoading(true);
    try {
      // Revoke the session on the server when possible, but always sign out on this
      // device: an expired session or a dropped connection must never trap the user.
      await apiRequest<void>("/auth/logout", { method: "POST", token }).catch(() => undefined);
      await clearSession();
      setNotice(null);
    } finally {
      setAccountLoading(false);
    }
  }, [clearSession, setNotice, token]);

  const deleteAccount = useCallback(async () => {
    if (!token) return;
    setAccountLoading(true);
    try {
      await apiRequest<void>("/auth/account", { method: "DELETE", token });
      await clearSession();
      setNotice(null);
    } finally {
      setAccountLoading(false);
    }
  }, [clearSession, setNotice, token]);

  const value = useMemo(
    () => ({
      account,
      accountLoading,
      clearNotice: () => setNotice(null),
      deleteAccount,
      error,
      linkIdentity,
      notice,
      providerConfig,
      ready,
      retry: () => setAttempt((value) => value + 1),
      signIn,
      signInWithEmailTestAccess,
      signOut,
      token,
    }),
    [
      account,
      accountLoading,
      deleteAccount,
      error,
      linkIdentity,
      notice,
      providerConfig,
      ready,
      signIn,
      signInWithEmailTestAccess,
      signOut,
      token,
    ],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider");
  return context;
}
