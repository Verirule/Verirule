import { LegalDocument } from "@/src/components/legal/LegalDocument";

const sections = [
  {
    heading: "Acceptable Use",
    paragraphs: [
      "Users must access Verirule only for lawful compliance and risk-management activities authorized by their organization.",
      "Any attempt to disrupt service, bypass controls, or scrape restricted data is prohibited.",
    ],
  },
  {
    heading: "Workspace Governance",
    paragraphs: [
      "Workspace owners are responsible for assigning appropriate roles and ensuring users follow internal governance requirements.",
      "Actions performed in Verirule may be logged for accountability and operational security.",
    ],
  },
  {
    heading: "Third-Party Integrations",
    paragraphs: [
      "Integrations with tools such as Slack, Jira, and GitHub are configured by customers and may transfer selected records for workflow automation.",
      "Organizations should review connected services to ensure they meet internal policy requirements.",
    ],
  },
  {
    heading: "Enforcement",
    paragraphs: [
      "Verirule may restrict or suspend access when activity violates this policy or threatens platform security.",
      "Serious misuse can result in account termination and additional legal remedies where applicable.",
    ],
  },
] as const;

export default function PolicyPage() {
  return (
    <LegalDocument
      title="Policy"
      summary="This policy outlines expected behavior and operational controls for all users of the Verirule platform."
      lastUpdated="February 10, 2026"
      sections={[...sections]}
    />
  );
}
