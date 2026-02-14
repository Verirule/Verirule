from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.controls import (
    ControlDetailOut,
    ControlEvidenceItemOut,
    ControlGuidanceOut,
    ControlOut,
    ControlSuggestionOut,
    FindingControlOut,
    InstallControlsFromTemplateIn,
    InstallControlsFromTemplateOut,
    LinkFindingToControlIn,
    LinkFindingToControlOut,
    OrgControlOut,
    OrgControlPatchIn,
)
from app.auth.roles import enforce_org_role
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    get_control_by_id,
    get_control_guidance,
    list_control_evidence,
    list_control_evidence_for_controls,
    list_controls,
    list_controls_by_ids,
    list_finding_controls,
    list_finding_controls_by_org,
    list_org_controls,
    patch_org_control_status,
    rpc_install_controls_for_template,
    rpc_link_finding_to_control,
    select_finding_by_id,
    select_findings,
    select_latest_finding_explanation,
    select_source_by_id,
)
from app.services.control_suggest import suggest_controls_for_finding

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


def _clean_framework_slug(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _clean_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _build_control_payload(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": row.get("id"),
        "framework_slug": row.get("framework_slug"),
        "control_key": row.get("control_key"),
        "title": row.get("title"),
        "description": row.get("description"),
        "severity_default": row.get("severity_default"),
        "tags": _clean_tags(row.get("tags")),
        "created_at": row.get("created_at"),
    }


def _ensure_finding_in_org(finding_row: dict[str, object] | None, org_id: UUID) -> dict[str, object]:
    if finding_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")
    if finding_row.get("org_id") != str(org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")
    return finding_row


@router.get("/controls")
async def controls(
    framework: str | None = None,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[ControlOut]]:
    rows = await list_controls(auth.access_token, framework_slug=_clean_framework_slug(framework))
    payload = [ControlOut.model_validate(_build_control_payload(row)) for row in rows]
    return {"controls": payload}


@router.get("/controls/{control_id}")
async def control_details(
    control_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> ControlDetailOut:
    control_row = await get_control_by_id(auth.access_token, str(control_id))
    if control_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found.")

    evidence_rows = await list_control_evidence(auth.access_token, str(control_id))
    guidance_row = await get_control_guidance(auth.access_token, str(control_id))

    guidance = (
        ControlGuidanceOut.model_validate(guidance_row)
        if isinstance(guidance_row, dict)
        else None
    )
    evidence = [ControlEvidenceItemOut.model_validate(row) for row in evidence_rows]
    return ControlDetailOut(
        control=ControlOut.model_validate(_build_control_payload(control_row)),
        evidence=evidence,
        guidance=guidance,
    )


@router.post("/orgs/{org_id}/controls/install-from-template")
async def install_controls_from_template(
    org_id: UUID,
    payload: InstallControlsFromTemplateIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> InstallControlsFromTemplateOut:
    await enforce_org_role(auth, str(org_id), "member")
    installed = await rpc_install_controls_for_template(
        auth.access_token,
        str(org_id),
        payload.template_slug.strip().lower(),
    )
    return InstallControlsFromTemplateOut(installed=installed)


@router.get("/orgs/{org_id}/controls")
async def org_controls(
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[OrgControlOut]]:
    await enforce_org_role(auth, str(org_id), "member")
    org_control_rows = await list_org_controls(auth.access_token, str(org_id))
    if not org_control_rows:
        return {"controls": []}

    control_ids = sorted(
        {
            str(row.get("control_id"))
            for row in org_control_rows
            if isinstance(row.get("control_id"), str)
        }
    )
    control_rows = await list_controls_by_ids(auth.access_token, control_ids)
    control_by_id = {
        str(row.get("id")): row for row in control_rows if isinstance(row.get("id"), str)
    }

    evidence_rows = await list_control_evidence_for_controls(auth.access_token, control_ids)
    evidence_count_by_control: dict[str, int] = defaultdict(int)
    for evidence in evidence_rows:
        control_id = evidence.get("control_id")
        if isinstance(control_id, str):
            evidence_count_by_control[control_id] += 1

    finding_links = await list_finding_controls_by_org(auth.access_token, str(org_id))
    links_by_control: dict[str, list[dict[str, object]]] = defaultdict(list)
    for link in finding_links:
        control_id = link.get("control_id")
        if isinstance(control_id, str):
            links_by_control[control_id].append(link)

    finding_rows = await select_findings(auth.access_token, str(org_id))
    finding_by_id = {
        str(row.get("id")): row for row in finding_rows if isinstance(row.get("id"), str)
    }

    payload: list[OrgControlOut] = []
    for org_control in org_control_rows:
        control_id = org_control.get("control_id")
        if not isinstance(control_id, str):
            continue
        control = control_by_id.get(control_id)
        if not isinstance(control, dict):
            continue

        linked_findings: list[dict[str, object]] = []
        for link in links_by_control.get(control_id, []):
            finding_id = link.get("finding_id")
            if not isinstance(finding_id, str):
                continue
            finding = finding_by_id.get(finding_id)
            if not isinstance(finding, dict):
                continue
            linked_findings.append(
                {
                    "finding_id": finding_id,
                    "title": finding.get("title"),
                    "summary": finding.get("summary"),
                    "severity": finding.get("severity"),
                    "detected_at": finding.get("detected_at"),
                    "confidence": link.get("confidence"),
                }
            )

        payload.append(
            OrgControlOut.model_validate(
                {
                    "id": org_control.get("id"),
                    "org_id": org_control.get("org_id"),
                    "control_id": control_id,
                    "status": org_control.get("status"),
                    "owner_user_id": org_control.get("owner_user_id"),
                    "notes": org_control.get("notes"),
                    "created_at": org_control.get("created_at"),
                    "framework_slug": control.get("framework_slug"),
                    "control_key": control.get("control_key"),
                    "title": control.get("title"),
                    "description": control.get("description"),
                    "severity_default": control.get("severity_default"),
                    "tags": _clean_tags(control.get("tags")),
                    "evidence_count": evidence_count_by_control.get(control_id, 0),
                    "linked_findings": linked_findings,
                }
            )
        )

    return {"controls": payload}


@router.patch("/org-controls/{org_control_id}")
async def patch_org_control(
    org_control_id: UUID,
    payload: OrgControlPatchIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> OrgControlOut:
    include_owner_user_id = "owner_user_id" in payload.model_fields_set
    include_notes = "notes" in payload.model_fields_set

    updated_org_control = await patch_org_control_status(
        auth.access_token,
        str(org_control_id),
        payload.status,
        str(payload.owner_user_id) if payload.owner_user_id else None,
        payload.notes,
        include_owner_user_id=include_owner_user_id,
        include_notes=include_notes,
    )
    if updated_org_control is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org control not found.")

    control_id = updated_org_control.get("control_id")
    if not isinstance(control_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid org control response from Supabase.",
        )
    control_row = await get_control_by_id(auth.access_token, control_id)
    if control_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found.")
    evidence_count = len(await list_control_evidence(auth.access_token, control_id))

    return OrgControlOut.model_validate(
        {
            "id": updated_org_control.get("id"),
            "org_id": updated_org_control.get("org_id"),
            "control_id": control_id,
            "status": updated_org_control.get("status"),
            "owner_user_id": updated_org_control.get("owner_user_id"),
            "notes": updated_org_control.get("notes"),
            "created_at": updated_org_control.get("created_at"),
            "framework_slug": control_row.get("framework_slug"),
            "control_key": control_row.get("control_key"),
            "title": control_row.get("title"),
            "description": control_row.get("description"),
            "severity_default": control_row.get("severity_default"),
            "tags": _clean_tags(control_row.get("tags")),
            "evidence_count": evidence_count,
            "linked_findings": [],
        }
    )


@router.get("/findings/{finding_id}/controls")
async def finding_controls(
    finding_id: UUID,
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[FindingControlOut]]:
    await enforce_org_role(auth, str(org_id), "member")
    finding_row = await select_finding_by_id(auth.access_token, str(finding_id))
    _ensure_finding_in_org(finding_row, org_id)

    linked_rows = await list_finding_controls(auth.access_token, str(org_id), str(finding_id))
    if not linked_rows:
        return {"controls": []}

    control_ids = sorted(
        {
            str(row.get("control_id"))
            for row in linked_rows
            if isinstance(row.get("control_id"), str)
        }
    )
    controls_rows = await list_controls_by_ids(auth.access_token, control_ids)
    controls_by_id = {
        str(row.get("id")): row for row in controls_rows if isinstance(row.get("id"), str)
    }

    payload: list[FindingControlOut] = []
    for link in linked_rows:
        control_id = link.get("control_id")
        if not isinstance(control_id, str):
            continue
        control = controls_by_id.get(control_id)
        if not isinstance(control, dict):
            continue

        payload.append(
            FindingControlOut.model_validate(
                {
                    "id": link.get("id"),
                    "org_id": link.get("org_id"),
                    "finding_id": link.get("finding_id"),
                    "control_id": control_id,
                    "confidence": link.get("confidence"),
                    "created_at": link.get("created_at"),
                    "framework_slug": control.get("framework_slug"),
                    "control_key": control.get("control_key"),
                    "title": control.get("title"),
                    "severity_default": control.get("severity_default"),
                    "tags": _clean_tags(control.get("tags")),
                }
            )
        )

    return {"controls": payload}


@router.post("/findings/{finding_id}/controls")
async def link_finding_to_control(
    finding_id: UUID,
    payload: LinkFindingToControlIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> LinkFindingToControlOut:
    await enforce_org_role(auth, str(payload.org_id), "member")
    finding_row = await select_finding_by_id(auth.access_token, str(finding_id))
    _ensure_finding_in_org(finding_row, payload.org_id)

    await rpc_link_finding_to_control(
        auth.access_token,
        str(payload.org_id),
        str(finding_id),
        str(payload.control_id),
        payload.confidence,
    )
    return LinkFindingToControlOut(ok=True)


@router.get("/findings/{finding_id}/controls/suggest")
async def suggest_finding_controls(
    finding_id: UUID,
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[ControlSuggestionOut]]:
    finding_row = _ensure_finding_in_org(
        await select_finding_by_id(auth.access_token, str(finding_id)),
        org_id,
    )
    explanation = await select_latest_finding_explanation(auth.access_token, str(finding_id))

    template_tags: list[str] = []
    source_id = finding_row.get("source_id")
    if isinstance(source_id, str):
        source = await select_source_by_id(auth.access_token, source_id)
        if isinstance(source, dict):
            template_tags = _clean_tags(source.get("tags"))

    org_control_rows = await list_org_controls(auth.access_token, str(org_id))
    org_control_ids = [
        str(row.get("control_id"))
        for row in org_control_rows
        if isinstance(row.get("control_id"), str)
    ]
    if org_control_ids:
        control_catalog = await list_controls_by_ids(auth.access_token, org_control_ids)
    else:
        control_catalog = await list_controls(auth.access_token)

    existing_links = await list_finding_controls(auth.access_token, str(org_id), str(finding_id))
    existing_control_ids = {
        str(row.get("control_id"))
        for row in existing_links
        if isinstance(row.get("control_id"), str)
    }

    suggestions = suggest_controls_for_finding(
        finding=finding_row,
        explanation=explanation,
        template_tags=template_tags,
        control_catalog=control_catalog,
    )
    payload: list[ControlSuggestionOut] = []
    for suggestion in suggestions:
        control_id = suggestion.get("control_id")
        if not isinstance(control_id, str) or control_id in existing_control_ids:
            continue
        payload.append(
            ControlSuggestionOut.model_validate(
                {
                    "control_id": control_id,
                    "framework_slug": suggestion.get("framework_slug"),
                    "control_key": suggestion.get("control_key"),
                    "title": suggestion.get("title"),
                    "confidence": suggestion.get("confidence"),
                    "reasons": suggestion.get("reasons") if isinstance(suggestion.get("reasons"), list) else [],
                }
            )
        )

    return {"suggestions": payload}
