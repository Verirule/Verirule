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
    <div className="min-h-screen bg-[radial-gradient(circle_at_12%_18%,#0B6FBF50_0%,transparent_40%),radial-gradient(circle_at_88%_10%,#4B96D845_0%,transparent_36%),radial-gradient(circle_at_62%_88%,#9ED4FF36_0%,transparent_34%),linear-gradient(180deg,#08243D_0%,#0A3B63_100%)] text-[#ecf7ff]">
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
