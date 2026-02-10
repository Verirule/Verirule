import { LegalDocument } from "@/src/components/legal/LegalDocument";

const sections = [
  {
    heading: "Service Availability",
    paragraphs: [
      "Verirule is designed for continuous compliance monitoring with commercially reasonable efforts to maintain high availability.",
      "Planned maintenance windows and incident updates are communicated through standard support channels.",
    ],
  },
  {
    heading: "Support Coverage",
    paragraphs: [
      "Support is provided for account access, core monitoring workflows, integrations, and issue triage.",
      "Response targets may vary by plan, severity, and contractual commitments.",
    ],
  },
  {
    heading: "Change Management",
    paragraphs: [
      "Platform updates may include security enhancements, regulatory source improvements, and workflow capabilities.",
      "Material changes that affect customer operations are announced in advance whenever possible.",
    ],
  },
  {
    heading: "Service Limits",
    paragraphs: [
      "Capacity limits, API use thresholds, and integration quotas may apply based on subscribed plan tiers.",
      "Customers can contact Verirule to review scaling options for higher-volume compliance operations.",
    ],
  },
] as const;

export default function ServicePage() {
  return (
    <LegalDocument
      title="Service"
      summary="This page describes platform operations, support scope, and service management commitments."
      lastUpdated="February 10, 2026"
      sections={[...sections]}
    />
  );
}
