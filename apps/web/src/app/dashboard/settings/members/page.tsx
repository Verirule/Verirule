"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

type OrgRecord = {
  id: string;
  name: string;
  created_at: string;
};

type MemberRole = "owner" | "admin" | "member" | "viewer";
type InviteRole = "admin" | "member" | "viewer";

type MemberRecord = {
  org_id: string;
  user_id: string;
  role: MemberRole;
  created_at: string;
};

type InviteRecord = {
  id: string;
  org_id: string;
  email: string;
  role: InviteRole;
  invited_by: string | null;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
};

type MeResponse = {
  sub?: unknown;
};

type OrgsResponse = { orgs: OrgRecord[] };
type MembersResponse = { members: MemberRecord[] };
type InvitesResponse = { invites: InviteRecord[] };

function roleBadgeClass(role: MemberRole | InviteRole): string {
  if (role === "owner") return "bg-amber-100 text-amber-900";
  if (role === "admin") return "bg-blue-100 text-blue-800";
  if (role === "member") return "bg-emerald-100 text-emerald-800";
  return "bg-slate-100 text-slate-700";
}

function formatDateTime(value: string | null): string {
  if (!value) return "N/A";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "N/A";
  return parsed.toLocaleString();
}

export default function DashboardSettingsMembersPage() {
  const [orgs, setOrgs] = useState<OrgRecord[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [members, setMembers] = useState<MemberRecord[]>([]);
  const [invites, setInvites] = useState<InviteRecord[]>([]);
  const [currentUserId, setCurrentUserId] = useState("");

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<InviteRole>("member");
  const [inviteExpiresHours, setInviteExpiresHours] = useState(72);

  const [isLoadingOrgs, setIsLoadingOrgs] = useState(true);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [isLoadingInvites, setIsLoadingInvites] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const [removingUserId, setRemovingUserId] = useState<string | null>(null);
  const [revokingInviteId, setRevokingInviteId] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showUpgradeCta, setShowUpgradeCta] = useState(false);

  const currentUserRole = useMemo(() => {
    if (!currentUserId) return null;
    return members.find((member) => member.user_id === currentUserId)?.role ?? null;
  }, [members, currentUserId]);

  const canManageMembers = currentUserRole === "owner" || currentUserRole === "admin";
  const isOwner = currentUserRole === "owner";

  const loadMe = useCallback(async () => {
    try {
      const response = await fetch("/api/me", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as MeResponse;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      setCurrentUserId(typeof body.sub === "string" ? body.sub : "");
    } catch {
      setCurrentUserId("");
    }
  }, []);

  const loadOrgs = useCallback(async () => {
    setIsLoadingOrgs(true);
    setError(null);

    try {
      const response = await fetch("/api/orgs", { method: "GET", cache: "no-store" });
      const body = (await response.json().catch(() => ({}))) as Partial<OrgsResponse>;

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.orgs)) {
        setError("Unable to load workspaces.");
        setOrgs([]);
        setSelectedOrgId("");
        return;
      }

      const rows = body.orgs;
      setOrgs(rows);
      setSelectedOrgId((current) => {
        if (current && rows.some((org) => org.id === current)) {
          return current;
        }
        return rows[0]?.id ?? "";
      });
    } catch {
      setError("Unable to load workspaces.");
      setOrgs([]);
      setSelectedOrgId("");
    } finally {
      setIsLoadingOrgs(false);
    }
  }, []);

  const loadMembers = useCallback(async (orgId: string) => {
    if (!orgId) {
      setMembers([]);
      return;
    }

    setIsLoadingMembers(true);
    setError(null);

    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/members`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<MembersResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || !Array.isArray(body.members)) {
        const detail = typeof body.message === "string" ? body.message : "Unable to load members.";
        setError(detail);
        setMembers([]);
        return;
      }

      setMembers(body.members);
    } catch {
      setError("Unable to load members.");
      setMembers([]);
    } finally {
      setIsLoadingMembers(false);
    }
  }, []);

  const loadInvites = useCallback(async (orgId: string) => {
    if (!orgId) {
      setInvites([]);
      return;
    }

    setIsLoadingInvites(true);

    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(orgId)}/invites`, {
        method: "GET",
        cache: "no-store",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<InvitesResponse> & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (response.status === 403) {
        setInvites([]);
        return;
      }

      if (!response.ok || !Array.isArray(body.invites)) {
        const detail = typeof body.message === "string" ? body.message : "Unable to load pending invites.";
        setError(detail);
        setInvites([]);
        return;
      }

      setInvites(body.invites);
    } catch {
      setError("Unable to load pending invites.");
      setInvites([]);
    } finally {
      setIsLoadingInvites(false);
    }
  }, []);

  useEffect(() => {
    void loadMe();
    void loadOrgs();
  }, [loadMe, loadOrgs]);

  useEffect(() => {
    if (!selectedOrgId) {
      setMembers([]);
      setInvites([]);
      return;
    }

    void loadMembers(selectedOrgId);
    void loadInvites(selectedOrgId);
  }, [selectedOrgId, loadMembers, loadInvites]);

  const submitInvite = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setShowUpgradeCta(false);

    if (!canManageMembers || !selectedOrgId) {
      setError("Only admins and owners can create invites.");
      return;
    }

    if (!inviteEmail.trim()) {
      setError("Email is required.");
      return;
    }

    setIsInviting(true);
    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(selectedOrgId)}/invites`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: inviteEmail.trim(),
          role: inviteRole,
          expires_hours: inviteExpiresHours,
        }),
      });
      const body = (await response.json().catch(() => ({}))) as {
        message?: unknown;
        invite_link?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const detail = typeof body.message === "string" ? body.message : "Unable to create invite.";
        setError(detail);
        setShowUpgradeCta(response.status === 402);
        return;
      }

      const link = typeof body.invite_link === "string" ? body.invite_link : "";
      if (link) {
        setSuccess(`Invite created. Development accept link: ${link}`);
      } else {
        setSuccess("Invite created and email dispatched.");
      }

      setInviteEmail("");
      setShowUpgradeCta(false);
      await loadInvites(selectedOrgId);
    } catch {
      setError("Unable to create invite.");
      setShowUpgradeCta(false);
    } finally {
      setIsInviting(false);
    }
  };

  const changeMemberRole = async (userId: string, nextRole: MemberRole) => {
    if (!selectedOrgId || !canManageMembers) {
      return;
    }

    setUpdatingUserId(userId);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(selectedOrgId)}/members`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, role: nextRole }),
      });
      const body = (await response.json().catch(() => ({}))) as MemberRecord & {
        message?: unknown;
      };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok || typeof body.user_id !== "string") {
        const detail = typeof body.message === "string" ? body.message : "Unable to update member role.";
        setError(detail);
        return;
      }

      setMembers((current) => current.map((member) => (member.user_id === userId ? body : member)));
      setSuccess("Member role updated.");
    } catch {
      setError("Unable to update member role.");
    } finally {
      setUpdatingUserId(null);
    }
  };

  const removeMember = async (userId: string) => {
    if (!selectedOrgId || !canManageMembers) {
      return;
    }

    setRemovingUserId(userId);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(`/api/orgs/${encodeURIComponent(selectedOrgId)}/members`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId }),
      });
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const detail = typeof body.message === "string" ? body.message : "Unable to remove member.";
        setError(detail);
        return;
      }

      setMembers((current) => current.filter((member) => member.user_id !== userId));
      setSuccess("Member removed.");
    } catch {
      setError("Unable to remove member.");
    } finally {
      setRemovingUserId(null);
    }
  };

  const revokeInvite = async (inviteId: string) => {
    if (!selectedOrgId || !canManageMembers) {
      return;
    }

    setRevokingInviteId(inviteId);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(
        `/api/orgs/${encodeURIComponent(selectedOrgId)}/invites/${encodeURIComponent(inviteId)}`,
        {
          method: "DELETE",
        },
      );
      const body = (await response.json().catch(() => ({}))) as { message?: unknown };

      if (response.status === 401) {
        window.location.href = "/auth/login";
        return;
      }

      if (!response.ok) {
        const detail = typeof body.message === "string" ? body.message : "Unable to revoke invite.";
        setError(detail);
        return;
      }

      setInvites((current) => current.filter((invite) => invite.id !== inviteId));
      setSuccess("Invite revoked.");
    } catch {
      setError("Unable to revoke invite.");
    } finally {
      setRevokingInviteId(null);
    }
  };

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Members</h1>
          <Button asChild variant="outline" size="sm">
            <Link href="/dashboard/settings">Back to settings</Link>
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">
          Manage organization membership, role delegation, and invitation lifecycle across global teams.
        </p>
      </section>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Workspace Scope</CardTitle>
          <CardDescription>Select the workspace where membership policies should be administered.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingOrgs ? <p className="text-sm text-muted-foreground">Loading workspaces...</p> : null}
          {!isLoadingOrgs && orgs.length > 0 ? (
            <div className="space-y-2">
              <Label htmlFor="members-org-selector">Workspace</Label>
              <select
                id="members-org-selector"
                value={selectedOrgId}
                onChange={(event) => setSelectedOrgId(event.target.value)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                {orgs.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          {currentUserRole ? (
            <p className="text-xs text-muted-foreground">
              Your workspace role: <span className="font-medium text-foreground">{currentUserRole}</span>
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Current Members</CardTitle>
          <CardDescription>Authorized identities and delegated governance roles for this workspace.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoadingMembers ? <p className="text-sm text-muted-foreground">Loading members...</p> : null}

          {!isLoadingMembers && members.length === 0 ? (
            <p className="text-sm text-muted-foreground">No members found for this workspace.</p>
          ) : null}

          {!isLoadingMembers && members.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border/70 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-2 py-2">User</th>
                    <th className="px-2 py-2">Role</th>
                    <th className="px-2 py-2">Joined</th>
                    <th className="px-2 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => {
                    const editingOwner = member.role === "owner";
                    const canEditRow = canManageMembers && (!editingOwner || isOwner);
                    const canRemoveRow =
                      canManageMembers && member.user_id !== currentUserId && (!editingOwner || isOwner);

                    return (
                      <tr key={member.user_id} className="border-b border-border/50">
                        <td className="px-2 py-2">
                          <div className="font-mono text-xs">{member.user_id}</div>
                        </td>
                        <td className="px-2 py-2">
                          {canEditRow ? (
                            <select
                              value={member.role}
                              onChange={(event) =>
                                void changeMemberRole(member.user_id, event.target.value as MemberRole)
                              }
                              disabled={updatingUserId === member.user_id}
                              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                            >
                              <option value="owner" disabled={!isOwner}>
                                owner
                              </option>
                              <option value="admin">admin</option>
                              <option value="member">member</option>
                              <option value="viewer">viewer</option>
                            </select>
                          ) : (
                            <span className={`rounded px-2 py-1 text-xs font-medium ${roleBadgeClass(member.role)}`}>
                              {member.role}
                            </span>
                          )}
                        </td>
                        <td className="px-2 py-2">{formatDateTime(member.created_at)}</td>
                        <td className="px-2 py-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            disabled={!canRemoveRow || removingUserId === member.user_id}
                            onClick={() => void removeMember(member.user_id)}
                          >
                            {removingUserId === member.user_id ? "Removing..." : "Remove"}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Invite Teammate</CardTitle>
          <CardDescription>Issue a role-scoped invitation and deliver a secure acceptance link by email.</CardDescription>
        </CardHeader>
        <CardContent>
          {canManageMembers ? (
            <form onSubmit={submitInvite} className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  value={inviteEmail}
                  onChange={(event) => setInviteEmail(event.target.value)}
                  placeholder="teammate@company.com"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="invite-role">Role</Label>
                  <select
                    id="invite-role"
                    value={inviteRole}
                    onChange={(event) => setInviteRole(event.target.value as InviteRole)}
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="admin">admin</option>
                    <option value="member">member</option>
                    <option value="viewer">viewer</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="invite-expires">Expires In (hours)</Label>
                  <Input
                    id="invite-expires"
                    type="number"
                    min={1}
                    max={720}
                    value={inviteExpiresHours}
                    onChange={(event) => setInviteExpiresHours(Number(event.target.value) || 72)}
                  />
                </div>
              </div>

              <Button type="submit" disabled={isInviting || !selectedOrgId}>
                {isInviting ? "Creating invite..." : "Create Invite"}
              </Button>
            </form>
          ) : (
            <p className="text-sm text-muted-foreground">Only admins and owners can create invites.</p>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/70">
        <CardHeader>
          <CardTitle>Pending Invites</CardTitle>
          <CardDescription>Outstanding invitations that have not been accepted.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {!canManageMembers ? (
            <p className="text-sm text-muted-foreground">Only admins and owners can view pending invites.</p>
          ) : null}

          {canManageMembers && isLoadingInvites ? (
            <p className="text-sm text-muted-foreground">Loading pending invites...</p>
          ) : null}

          {canManageMembers && !isLoadingInvites && invites.length === 0 ? (
            <p className="text-sm text-muted-foreground">No pending invites.</p>
          ) : null}

          {canManageMembers && !isLoadingInvites && invites.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border/70 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-2 py-2">Email</th>
                    <th className="px-2 py-2">Role</th>
                    <th className="px-2 py-2">Expires</th>
                    <th className="px-2 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invites.map((invite) => (
                    <tr key={invite.id} className="border-b border-border/50">
                      <td className="px-2 py-2">{invite.email}</td>
                      <td className="px-2 py-2">
                        <span className={`rounded px-2 py-1 text-xs font-medium ${roleBadgeClass(invite.role)}`}>
                          {invite.role}
                        </span>
                      </td>
                      <td className="px-2 py-2">{formatDateTime(invite.expires_at)}</td>
                      <td className="px-2 py-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={revokingInviteId === invite.id}
                          onClick={() => void revokeInvite(invite.id)}
                        >
                          {revokingInviteId === invite.id ? "Revoking..." : "Revoke"}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {error ? (
        <div className="space-y-2">
          <p className="text-sm text-destructive">{error}</p>
          {showUpgradeCta ? (
            <Button asChild size="sm" variant="outline">
              <Link href="/dashboard/billing">Upgrade plan</Link>
            </Button>
          ) : null}
        </div>
      ) : null}
      {success ? <p className="text-sm text-emerald-700">{success}</p> : null}
    </div>
  );
}
