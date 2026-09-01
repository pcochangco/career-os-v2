import { Stack, usePathname } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AppErrorBoundary } from "@/components/app-error-boundary";
import { SessionProvider } from "@/lib/session";
import { ThemeProvider, useTheme } from "@/lib/theme";

function AppNavigator() {
  const { isDark } = useTheme();
  const pathname = usePathname();
  const publicRoute = ["/account-deletion", "/privacy", "/support", "/terms"].includes(pathname);
  return (
    <>
      <StatusBar style={isDark ? "light" : "dark"} />
      <AppErrorBoundary>
        <SessionProvider enabled={!publicRoute}>
          <Stack screenOptions={{ headerShown: false }} />
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
