import { usePathname, useRouter } from "expo-router";
import { LayoutList, LucideIcon, Plus, Settings } from "@/components/icons";
import { createContext, ReactNode, useContext } from "react";
import { Image, Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { breakpoints, radius, ThemeColors, useTheme } from "@/lib/theme";

type ShellContextValue = { inShell: boolean; wide: boolean };

const ShellContext = createContext<ShellContextValue>({ inShell: false, wide: false });

/** Whether the current screen renders inside the signed-in app shell, and at which size. */
export function useShell(): ShellContextValue {
  return useContext(ShellContext);
}

/** True when the window is wide enough for the desktop layout. */
export function useIsWide(): boolean {
  const { width } = useWindowDimensions();
  return width >= breakpoints.desktop;
}

type NavItem = { href: string; icon: LucideIcon; label: string; match: (path: string) => boolean };

const navItems: NavItem[] = [
  {
    href: "/goals",
    icon: LayoutList,
    label: "Goals",
    match: (path) => path === "/goals" || (path.startsWith("/goals/") && path !== "/goals/new"),
  },
  { href: "/goals/new", icon: Plus, label: "New goal", match: (path) => path === "/goals/new" },
  {
    href: "/settings",
    icon: Settings,
    label: "Settings",
    match: (path) => path === "/settings" || path === "/report-issue",
  },
];

/**
 * Navigation chrome around every screen. Public pages render it with `chrome={false}` instead of
 * leaving it out, so signing in doesn't rebuild (and remount) the screen underneath.
 */
export function AppShell({ children, chrome = true }: { children: ReactNode; chrome?: boolean }) {
  const { colors } = useTheme();
  const wide = useIsWide();
  const styles = createStyles(colors);

  return (
    <ShellContext.Provider value={{ inShell: chrome, wide }}>
      <View style={wide ? styles.row : styles.column}>
        {chrome && wide ? <Sidebar /> : null}
        <View style={styles.main}>{children}</View>
        {chrome && !wide ? <BottomTabs /> : null}
      </View>
    </ShellContext.Provider>
  );
}

function Sidebar() {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const pathname = usePathname();
  const router = useRouter();

  return (
    <View role="navigation" style={styles.sidebar}>
      <Pressable
        accessibilityLabel="CareerOS home"
        accessibilityRole="link"
        onPress={() => router.push("/goals" as never)}
        style={styles.sidebarBrand}
      >
        <Image
          accessibilityIgnoresInvertColors
          source={require("../../assets/logo-mark.png")}
          style={styles.sidebarMark}
        />
        <Text style={styles.sidebarBrandText}>CareerOS</Text>
      </Pressable>
      <View style={styles.sidebarNav}>
        {navItems.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;
          return (
            <Pressable
              accessibilityRole="link"
              accessibilityState={{ selected: active }}
              key={item.href}
              onPress={() => router.push(item.href as never)}
              style={({ hovered, pressed }: { hovered?: boolean; pressed: boolean }) => [
                styles.sidebarItem,
                (hovered || pressed) && !active && { backgroundColor: colors.hover },
                active && { backgroundColor: colors.forestSoft },
              ]}
            >
              <Icon color={active ? colors.forest : colors.muted} size={18} strokeWidth={2} />
              <Text style={[styles.sidebarLabel, active && { color: colors.forestDark, fontWeight: "700" }]}>
                {item.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function BottomTabs() {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const pathname = usePathname();
  const router = useRouter();
  const insets = useSafeAreaInsets();

  return (
    <View
      accessibilityRole="tablist"
      style={[styles.tabs, { paddingBottom: Math.max(insets.bottom, 6) }]}
    >
      {navItems.map((item) => {
        const active = item.match(pathname);
        const Icon = item.icon;
        return (
          <Pressable
            accessibilityLabel={item.label}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            key={item.href}
            onPress={() => router.push(item.href as never)}
            style={({ pressed }) => [styles.tab, pressed && { opacity: 0.7 }]}
          >
            <View style={[styles.tabIcon, active && { backgroundColor: colors.forestSoft }]}>
              <Icon color={active ? colors.forest : colors.subtle} size={20} strokeWidth={2} />
            </View>
            <Text style={[styles.tabLabel, { color: active ? colors.forestDark : colors.subtle }, active && { fontWeight: "700" }]}>
              {item.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const createStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    row: { backgroundColor: colors.background, flex: 1, flexDirection: "row" },
    column: { backgroundColor: colors.background, flex: 1 },
    main: { flex: 1, minWidth: 0 },
    sidebar: {
      backgroundColor: colors.card,
      borderRightColor: colors.line,
      borderRightWidth: 1,
      paddingHorizontal: 12,
      paddingVertical: 20,
      width: 240,
    },
    sidebarBrand: { alignItems: "center", flexDirection: "row", gap: 10, marginBottom: 24, paddingHorizontal: 8 },
    sidebarMark: { height: 28, width: 28 },
    sidebarBrandText: { color: colors.ink, fontSize: 16, fontWeight: "800", letterSpacing: 0.2 },
    sidebarNav: { gap: 2 },
    sidebarItem: {
      alignItems: "center",
      borderRadius: radius.md,
      flexDirection: "row",
      gap: 10,
      minHeight: 44,
      paddingHorizontal: 10,
    },
    sidebarLabel: { color: colors.muted, fontSize: 15, fontWeight: "500" },
    tabs: {
      backgroundColor: colors.card,
      borderTopColor: colors.line,
      borderTopWidth: 1,
      flexDirection: "row",
      paddingTop: 6,
    },
    tab: { alignItems: "center", flex: 1, gap: 2, justifyContent: "center", minHeight: 52 },
    tabIcon: { alignItems: "center", borderRadius: radius.pill, height: 30, justifyContent: "center", width: 52 },
    tabLabel: { fontSize: 12, fontWeight: "500" },
  });
