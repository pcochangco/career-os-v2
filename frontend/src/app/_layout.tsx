import { Stack, usePathname, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ReactNode, useEffect, useState } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AppErrorBoundary } from "@/components/app-error-boundary";
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
  if (publicRoute) return children;
  if (!session.ready || !session.token) return <LoadingState label="Sign in to continue…" />;
  return children;
}

function AppNavigator() {
  const { isDark } = useTheme();
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
