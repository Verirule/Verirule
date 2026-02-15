import { FAQ } from "@/src/components/marketing/FAQ";
import { FinalCTA } from "@/src/components/marketing/FinalCTA";
import { Hero } from "@/src/components/marketing/Hero";
import { HowItWorks } from "@/src/components/marketing/HowItWorks";
import { Integrations } from "@/src/components/marketing/Integrations";
import { MarketingNav } from "@/src/components/marketing/MarketingNav";
import { PillarsBento } from "@/src/components/marketing/PillarsBento";
import { Pricing } from "@/src/components/marketing/Pricing";
import { SecurityTrust } from "@/src/components/marketing/SecurityTrust";
import { SiteFooter } from "@/src/components/marketing/SiteFooter";
import { Workflows } from "@/src/components/marketing/Workflows";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0b1220] text-[#e9effb]">
      <MarketingNav />
      <main>
        <Hero />
        <PillarsBento />
        <HowItWorks />
        <Workflows />
        <Integrations />
        <Pricing />
        <SecurityTrust />
        <FAQ />
        <FinalCTA />
      </main>
      <SiteFooter />
    </div>
  );
}
