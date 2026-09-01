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

export type ProviderConfig = {
  apple: boolean;
  google: boolean;
  google_android_client_id: string;
  google_ios_client_id: string;
  google_web_client_id: string;
};

export type Account = {
  email: string;
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
  deleteAccount: () => Promise<void>;
  error: string | null;
  linkIdentity: (provider: IdentityProvider, identityToken: string) => Promise<void>;
  providerConfig: ProviderConfig;
  ready: boolean;
  retry: () => void;
  signIn: (provider: IdentityProvider, identityToken: string) => Promise<string>;
  signOut: () => Promise<void>;
  token: string | null;
};

const EMPTY_PROVIDER_CONFIG: ProviderConfig = {
  apple: false,
  google: false,
  google_android_client_id: "",
  google_ios_client_id: "",
  google_web_client_id: "",
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

  const clearSession = useCallback(async () => {
    await removeStoredToken();
    setToken(null);
    setAccount(null);
  }, []);

  const activateSession = useCallback(async (session: SessionResponse): Promise<string> => {
    const nextAccount = await readAccount(session.access_token);
    if (nextAccount.status !== "saved") {
      throw new Error("A saved account is required to use CareerOS.");
    }
    await storeToken(session.access_token);
    setToken(session.access_token);
    setAccount(nextAccount);
    setProviderConfig(nextAccount.provider_config);
    return session.access_token;
  }, []);

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
        const config = await apiRequest<ProviderConfig>("/auth/config");
        if (active) setProviderConfig(config);

        const stored = await readStoredToken();
        if (stored) {
          try {
            const storedAccount = await readAccount(stored);
            if (storedAccount.status === "saved") {
              if (active) {
                setToken(stored);
                setAccount(storedAccount);
                setProviderConfig(storedAccount.provider_config);
              }
            } else {
              await removeStoredToken();
            }
          } catch (caught) {
            if (!(caught instanceof ApiError) || caught.status !== 401) throw caught;
            await removeStoredToken();
          }
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
      await apiRequest<void>("/auth/logout", { method: "POST", token });
      await clearSession();
    } finally {
      setAccountLoading(false);
    }
  }, [clearSession, token]);

  const deleteAccount = useCallback(async () => {
    if (!token) return;
    setAccountLoading(true);
    try {
      await apiRequest<void>("/auth/account", { method: "DELETE", token });
      await clearSession();
    } finally {
      setAccountLoading(false);
    }
  }, [clearSession, token]);

  const value = useMemo(
    () => ({
      account,
      accountLoading,
      deleteAccount,
      error,
      linkIdentity,
      providerConfig,
      ready,
      retry: () => setAttempt((value) => value + 1),
      signIn,
      signOut,
      token,
    }),
    [
      account,
      accountLoading,
      deleteAccount,
      error,
      linkIdentity,
      providerConfig,
      ready,
      signIn,
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
