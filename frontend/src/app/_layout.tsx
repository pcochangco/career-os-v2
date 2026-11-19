import { Stack, usePathname, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ReactNode, useEffect, useState } from "react";
import { Platform } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AppErrorBoundary } from "@/components/app-error-boundary";
import { AppShell } from "@/components/app-shell";
import { LoadingState } from "@/components/ui";
import { SessionProvider, useSession } from "@/lib/session";
import { ThemeProvider, useTheme } from "@/lib/theme";

const publicRoutes = ["/", "/account-deletion", "/privacy", "/support", "/terms"];

function AuthGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const session = useSession();
  const [mounted, setMounted] = useState(false);
  const publicRoute = publicRoutes.includes(pathname);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (mounted && !publicRoute && session.ready && !session.token) router.replace("/");
  }, [mounted, publicRoute, router, session.ready, session.token]);

  if (!mounted) return <LoadingState />;
  if (!publicRoute && (!session.ready || !session.token)) {
    return <LoadingState label="Sign in to continue…" />;
  }
  return <AppShell chrome={!publicRoute}>{children}</AppShell>;
}

/**
 * Web only: a visible ring on whatever has keyboard focus. `:focus-visible` means mouse and
 * touch users never see it; Tab users always do. Text inputs already show a focused border.
 */
function useKeyboardFocusRing(color: string) {
  useEffect(() => {
    if (Platform.OS !== "web" || typeof document === "undefined") return;
    const style = document.createElement("style");
    style.setAttribute("data-careeros", "focus-ring");
    style.textContent =
      `[tabindex]:not(input):not(textarea):focus-visible, a:focus-visible, button:focus-visible ` +
      `{ outline: 2px solid ${color} !important; outline-offset: 2px; }`;
    document.head.appendChild(style);
    return () => style.remove();
  }, [color]);
}

function AppNavigator() {
  const { colors, isDark } = useTheme();
  useKeyboardFocusRing(colors.forest);
  return (
    <>
      <StatusBar style={isDark ? "light" : "dark"} />
      <AppErrorBoundary>
        <SessionProvider>
          <AuthGate>
            <Stack screenOptions={{ headerShown: false }} />
          </AuthGate>
        </SessionProvider>
      </AppErrorBoundary>
    </>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AppNavigator />
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
