import { LegalDocument } from "@/src/components/legal/LegalDocument";

const sections = [
  {
    heading: "Agreement Scope",
    paragraphs: [
      "These Terms govern access to Verirule services and apply to all users who access any workspace, API, or related application component.",
      "By using the service, you confirm you have authority to bind yourself or your organization to these Terms.",
    ],
  },
  {
    heading: "Customer Responsibilities",
    paragraphs: [
      "Customers are responsible for configuring sources, assigning users, and reviewing generated compliance insights before taking regulated actions.",
      "You must keep account credentials secure and notify Verirule promptly of any suspected unauthorized access.",
    ],
  },
  {
    heading: "Intellectual Property",
    paragraphs: [
      "Verirule retains all rights to the platform, software, and related materials except where open-source licensing terms apply.",
      "Customer data and uploaded evidence remain under customer control subject to contractual and legal obligations.",
    ],
  },
  {
    heading: "Limitation and Updates",
    paragraphs: [
      "The service provides operational support and does not replace legal advice. Customers remain responsible for final compliance decisions.",
      "Verirule may update these Terms with notice through the platform or other reasonable channels.",
    ],
  },
] as const;

export default function TermsPage() {
  return (
    <LegalDocument
      title="Terms"
      summary="These Terms define the legal framework for using Verirule products and related services."
      lastUpdated="February 10, 2026"
      sections={[...sections]}
    />
  );
}
