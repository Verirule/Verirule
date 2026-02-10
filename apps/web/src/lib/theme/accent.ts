export const ACCENT_STORAGE_KEY = "verirule.accent.color";
export const DEFAULT_ACCENT = "#38BDF8";

export function normalizeHexColor(value: string | null | undefined): string {
  if (!value) {
    return DEFAULT_ACCENT;
  }

  const trimmed = value.trim();
  const validHex = /^#([0-9a-fA-F]{6})$/;
  if (!validHex.test(trimmed)) {
    return DEFAULT_ACCENT;
  }

  return trimmed.toUpperCase();
}

export function getContrastForeground(hexColor: string): string {
  const color = normalizeHexColor(hexColor).replace("#", "");
  const red = parseInt(color.slice(0, 2), 16);
  const green = parseInt(color.slice(2, 4), 16);
  const blue = parseInt(color.slice(4, 6), 16);

  // WCAG relative luminance approximation for contrast-aware foreground color.
  const luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255;
  return luminance > 0.6 ? "#082F49" : "#F8FAFC";
}

export function applyAccentToDocument(hexColor: string): string {
  const normalized = normalizeHexColor(hexColor);

  if (typeof document === "undefined") {
    return normalized;
  }

  document.documentElement.style.setProperty("--vr-user-accent", normalized);
  document.documentElement.style.setProperty(
    "--vr-user-accent-foreground",
    getContrastForeground(normalized),
  );
  return normalized;
}
