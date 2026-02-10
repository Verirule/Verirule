import { LegalDocument } from "@/src/components/legal/LegalDocument";

const sections = [
  {
    heading: "Information We Collect",
    paragraphs: [
      "We collect account details such as name, email address, and authentication identifiers when you create or access a Verirule workspace.",
      "Operational data includes regulatory sources, findings, tasks, audit evidence metadata, and integration settings configured by your organization.",
    ],
  },
  {
    heading: "How We Use Information",
    paragraphs: [
      "We use data to provide compliance monitoring, send alerts, route tasks, and maintain an auditable action trail inside your workspace.",
      "We also use limited telemetry to maintain service reliability, detect abuse, and improve platform performance.",
    ],
  },
  {
    heading: "Security and Retention",
    paragraphs: [
      "Verirule uses role-based access controls, encrypted transport, and audit logging to protect customer data.",
      "Data retention is based on workspace configuration, legal obligations, and contractual commitments.",
    ],
  },
  {
    heading: "Your Rights",
    paragraphs: [
      "Depending on jurisdiction, users may request access, correction, deletion, or export of personal data.",
      "Administrators can manage user access and data controls from workspace settings.",
    ],
  },
] as const;

export default function PrivacyPage() {
  return (
    <LegalDocument
      title="Privacy"
      summary="This Privacy notice explains how Verirule collects, uses, secures, and manages personal and operational data."
      lastUpdated="February 10, 2026"
      sections={[...sections]}
    />
  );
}
