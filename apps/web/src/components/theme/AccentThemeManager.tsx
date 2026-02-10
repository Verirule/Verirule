"use client";

import { useEffect } from "react";

import { ACCENT_STORAGE_KEY, DEFAULT_ACCENT, applyAccentToDocument, normalizeHexColor } from "@/src/lib/theme/accent";

export function AccentThemeManager() {
  useEffect(() => {
    const storedColor = normalizeHexColor(window.localStorage.getItem(ACCENT_STORAGE_KEY) ?? DEFAULT_ACCENT);
    applyAccentToDocument(storedColor);
  }, []);

  return null;
}
