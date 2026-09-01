import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { SessionProvider } from "@/lib/session";
import { ThemeProvider, useTheme } from "@/lib/theme";

function AppNavigator() {
  const { isDark } = useTheme();
  return (
    <>
      <StatusBar style={isDark ? "light" : "dark"} />
      <SessionProvider>
        <Stack screenOptions={{ headerShown: false }} />
      </SessionProvider>
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
