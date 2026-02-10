import { createClient } from "@/lib/supabase/server";
import { connection, NextResponse } from "next/server";

export async function GET() {
  await connection();

  const apiBaseUrl = process.env.VERIRULE_API_URL?.replace(/\/$/, "");

  if (!apiBaseUrl) {
    return NextResponse.json({ message: "API not configured" }, { status: 501 });
  }

  try {
    const supabase = await createClient();
    const { data, error } = await supabase.auth.getSession();
    const accessToken = data.session?.access_token;

    if (error || !accessToken) {
      return NextResponse.json({ message: "Unauthorized" }, { status: 401 });
    }

    const upstreamResponse = await fetch(`${apiBaseUrl}/api/v1/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!upstreamResponse.ok) {
      return NextResponse.json(
        { message: "Failed to fetch claims from API" },
        { status: 502 },
      );
    }

    const body = (await upstreamResponse.json().catch(() => ({}))) as unknown;
    return NextResponse.json(body, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : undefined;
    console.error("api/me proxy failed", { message });
    return NextResponse.json(
      { message: "Upstream API error" },
      { status: 502 },
    );
  }
}
