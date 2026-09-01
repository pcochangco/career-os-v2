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
import { Platform, useColorScheme } from "react-native";

export type ThemePreference = "system" | "light" | "dark";

export type ThemeColors = {
  accentMuted: string;
  background: string;
  card: string;
  cardMuted: string;
  danger: string;
  fieldPlaceholder: string;
  forest: string;
  forestDark: string;
  forestSoft: string;
  ink: string;
  line: string;
  muted: string;
  onForest: string;
  onForestMuted: string;
  softBorder: string;
  white: string;
};

const lightColors: ThemeColors = {
  accentMuted: "#D8E9DC",
  background: "#F6F8F4",
  card: "#FFFFFF",
  cardMuted: "#F0F3F0",
  danger: "#A13B32",
  fieldPlaceholder: "#7D8A82",
  forest: "#1E6044",
  forestDark: "#184634",
  forestSoft: "#DCEDE3",
  ink: "#17211B",
  line: "#D7E0D9",
  muted: "#607067",
  onForest: "#FFFFFF",
  onForestMuted: "#D8E9DC",
  softBorder: "#B7D5C0",
  white: "#FFFFFF",
};

const darkColors: ThemeColors = {
  accentMuted: "#A8D9BE",
  background: "#0D1410",
  card: "#17211B",
  cardMuted: "#121B16",
  danger: "#FF9B91",
  fieldPlaceholder: "#84958B",
  forest: "#69D39E",
  forestDark: "#B7E8CE",
  forestSoft: "#173829",
  ink: "#F1F7F3",
  line: "#2C3A32",
  muted: "#AAB9B0",
  onForest: "#07110C",
  onForestMuted: "#214D39",
  softBorder: "#315D46",
  white: "#F4FAF6",
};

const THEME_KEY = "careeros.theme";

type ThemeContextValue = {
  colors: ThemeColors;
  isDark: boolean;
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function isThemePreference(value: string | null): value is ThemePreference {
  return value === "system" || value === "light" || value === "dark";
}

function readWebPreference(): ThemePreference {
  if (typeof localStorage === "undefined") return "system";
  const stored = localStorage.getItem(THEME_KEY);
  return isThemePreference(stored) ? stored : "system";
}

async function storePreference(preference: ThemePreference): Promise<void> {
  if (Platform.OS === "web" && typeof localStorage !== "undefined") {
    localStorage.setItem(THEME_KEY, preference);
    return;
  }
  await SecureStore.setItemAsync(THEME_KEY, preference);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>("system");

  useEffect(() => {
    if (Platform.OS === "web") {
      setPreferenceState(readWebPreference());
      return;
    }
    let active = true;
    SecureStore.getItemAsync(THEME_KEY)
      .then((stored) => {
        if (active && isThemePreference(stored)) setPreferenceState(stored);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    void storePreference(next).catch(() => undefined);
  }, []);

  const isDark = preference === "dark" || (preference === "system" && systemScheme === "dark");
  const value = useMemo(
    () => ({ colors: isDark ? darkColors : lightColors, isDark, preference, setPreference }),
    [isDark, preference, setPreference],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside ThemeProvider");
  return context;
}
