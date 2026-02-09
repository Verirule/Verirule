import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { getPublicSupabaseEnv } from "@/lib/env";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// This check can be removed, it is just for tutorial purposes
const { url, key, problems } = getPublicSupabaseEnv();
export const hasEnvVars = Boolean(url && key && problems.length === 0);
