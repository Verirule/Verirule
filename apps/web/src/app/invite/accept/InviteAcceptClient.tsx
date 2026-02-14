"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useEffect, useState } from "react";

type AcceptResponse = {
  org_id?: unknown;
};

export function InviteAcceptClient() {
  const [status, setStatus] = useState<"pending" | "error">("pending");
  const [message, setMessage] = useState("Accepting your workspace invite...");

  useEffect(() => {
    const acceptInvite = async () => {
      const token = new URLSearchParams(window.location.search).get("token")?.trim() ?? "";
      if (!token) {
        setStatus("error");
        setMessage("Invite token is missing.");
        return;
      }

      try {
        const response = await fetch("/api/invites/accept", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        const body = (await response.json().catch(() => ({}))) as AcceptResponse & {
          message?: unknown;
        };

        if (response.status === 401) {
          window.location.href = "/auth/login";
          return;
        }

        if (!response.ok || typeof body.org_id !== "string") {
          const detail = typeof body.message === "string" ? body.message : "Unable to accept invite.";
          setStatus("error");
          setMessage(detail);
          return;
        }

        window.location.href = `/dashboard?org_id=${encodeURIComponent(body.org_id)}`;
      } catch {
        setStatus("error");
        setMessage("Unable to accept invite.");
      }
    };

    void acceptInvite();
  }, []);

  return (
    <div className="mx-auto mt-20 max-w-xl px-4">
      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace Invite</CardTitle>
          <CardDescription>Finalize membership to continue into your dashboard workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className={status === "error" ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
            {message}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
