import { BentoImpact } from "@/src/components/landing/BentoImpact";
import { ChangeImpactDemo } from "@/src/components/landing/ChangeImpactDemo";
import { FAQ } from "@/src/components/landing/FAQ";
import { FeatureGrid } from "@/src/components/landing/FeatureGrid";
import { Footer } from "@/src/components/landing/Footer";
import { Hero } from "@/src/components/landing/Hero";
import { HowItWorks } from "@/src/components/landing/HowItWorks";
import { Nav } from "@/src/components/landing/Nav";
import { Pricing } from "@/src/components/landing/Pricing";
import { Section } from "@/src/components/landing/Section";
import { Security } from "@/src/components/landing/Security";
import { TrustBar } from "@/src/components/landing/TrustBar";

export default function Home() {
  return (
    <div className="min-h-screen">
      <Nav />
      <main>
        <Hero />
        <TrustBar />
        <Section id="how" eyebrow="How it works" title="From signal to action in three steps">
          <HowItWorks />
        </Section>
        <Section id="features" eyebrow="Features" title="Purpose-built for policy and compliance teams">
          <div className="space-y-6">
            <BentoImpact />
            <ChangeImpactDemo />
            <FeatureGrid />
          </div>
        </Section>
        <Section id="pricing" eyebrow="Pricing" title="Start free and grow with your team">
          <Pricing />
        </Section>
        <Section id="security" eyebrow="Security" title="Practical controls, clear boundaries">
          <Security />
        </Section>
        <Section id="faq" eyebrow="FAQ" title="Answers to common questions">
          <FAQ />
        </Section>
      </main>
      <Footer />
    </div>
  );
}
