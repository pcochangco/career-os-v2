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
  hover: string;
  ink: string;
  line: string;
  muted: string;
  onForest: string;
  onForestMuted: string;
  softBorder: string;
  subtle: string;
  white: string;
};

// Neutral, low-chroma surfaces with the brand green reserved for actions,
// progress and the current step, so the one important thing on a screen stands out.
const lightColors: ThemeColors = {
  accentMuted: "#CFE6D7",
  background: "#F6F7F9",
  card: "#FFFFFF",
  cardMuted: "#F2F4F7",
  danger: "#B42318",
  fieldPlaceholder: "#8A94A6",
  forest: "#1E6044",
  forestDark: "#154A34",
  forestSoft: "#EAF4EE",
  hover: "#F2F4F7",
  ink: "#101828",
  line: "#E4E7EC",
  muted: "#475467",
  onForest: "#FFFFFF",
  onForestMuted: "#D6EBDD",
  softBorder: "#CFE3D6",
  subtle: "#667085",
  white: "#FFFFFF",
};

const darkColors: ThemeColors = {
  accentMuted: "#A8D9BE",
  background: "#0E1210",
  card: "#161B18",
  cardMuted: "#1B211D",
  danger: "#FDA29B",
  fieldPlaceholder: "#7E8B83",
  forest: "#5FCB95",
  forestDark: "#A7E3C3",
  forestSoft: "#16291F",
  hover: "#1F2622",
  ink: "#EEF2EF",
  line: "#29312C",
  muted: "#A3B0A8",
  onForest: "#06110B",
  onForestMuted: "#1E4A35",
  softBorder: "#2C4D3B",
  subtle: "#8C998F",
  white: "#F4FAF6",
};

/** Shared layout scale used by every screen. */
export const radius = { sm: 8, md: 10, lg: 12, pill: 999 } as const;
export const breakpoints = { desktop: 960 } as const;

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
