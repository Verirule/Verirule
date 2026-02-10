"use client";

import { useEffect, useMemo, useState } from "react";

import {
  ACCENT_STORAGE_KEY,
  DEFAULT_ACCENT,
  applyAccentToDocument,
  normalizeHexColor,
} from "@/src/lib/theme/accent";

const accentPresets = [
  { name: "Sky", color: "#38BDF8" },
  { name: "Emerald", color: "#10B981" },
  { name: "Blue", color: "#3B82F6" },
  { name: "Slate", color: "#64748B" },
  { name: "Rose", color: "#F43F5E" },
  { name: "Amber", color: "#F59E0B" },
] as const;

export function AccentThemePicker() {
  const [selectedAccent, setSelectedAccent] = useState(DEFAULT_ACCENT);

  useEffect(() => {
    const storedAccent = normalizeHexColor(window.localStorage.getItem(ACCENT_STORAGE_KEY) ?? DEFAULT_ACCENT);
    const normalized = applyAccentToDocument(storedAccent);
    setSelectedAccent(normalized);
  }, []);

  const selectedPresetName = useMemo(
    () => accentPresets.find((preset) => preset.color === selectedAccent)?.name ?? "Custom",
    [selectedAccent],
  );

  const handleAccentChange = (nextAccent: string) => {
    const normalized = applyAccentToDocument(nextAccent);
    setSelectedAccent(normalized);
    window.localStorage.setItem(ACCENT_STORAGE_KEY, normalized);
  };

  const resetAccent = () => {
    handleAccentChange(DEFAULT_ACCENT);
    window.localStorage.removeItem(ACCENT_STORAGE_KEY);
  };

  return (
    <section className="rounded-xl border border-border/70 bg-card p-6 shadow-sm">
      <h2 className="text-lg font-semibold tracking-tight">Theme</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Choose the accent color you prefer. Your selection is saved on this device.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {accentPresets.map((preset) => (
          <button
            key={preset.color}
            type="button"
            onClick={() => handleAccentChange(preset.color)}
            className="inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-xs font-medium transition-colors hover:bg-accent"
            aria-pressed={selectedAccent === preset.color}
          >
            <span
              className="h-3 w-3 rounded-full border border-black/20"
              style={{ backgroundColor: preset.color }}
              aria-hidden
            />
            {preset.name}
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <label htmlFor="accent-color" className="text-sm font-medium">
          Custom color
        </label>
        <input
          id="accent-color"
          type="color"
          value={selectedAccent}
          onChange={(event) => handleAccentChange(event.target.value)}
          className="h-9 w-12 cursor-pointer rounded-md border border-border bg-background p-1"
          aria-label="Pick accent color"
        />
        <button
          type="button"
          onClick={resetAccent}
          className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm font-medium transition-colors hover:bg-accent"
        >
          Reset to default
        </button>
      </div>

      <div className="mt-5 rounded-lg border border-border/70 bg-background p-4">
        <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Preview</p>
        <div className="mt-3 flex items-center gap-3">
          <span
            className="inline-flex rounded-md px-3 py-1.5 text-sm font-semibold"
            style={{
              backgroundColor: "var(--vr-user-accent)",
              color: "var(--vr-user-accent-foreground)",
            }}
          >
            {selectedPresetName}
          </span>
          <span className="text-sm text-muted-foreground">{selectedAccent}</span>
        </div>
      </div>
    </section>
  );
}
