import Link from "next/link";
import { TutorialStep } from "./tutorial-step";
import { ArrowUpRight } from "lucide-react";

const configuredSiteUrl = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");

export function SignUpUserSteps() {
  return (
    <ol className="flex flex-col gap-6">
      <TutorialStep title="Set up redirect urls">
        <p>Add your local and deployed callback URLs in Supabase Auth settings.</p>
        <p className="mt-4">
          You can manage this in{" "}
          <Link
            className="text-primary hover:text-foreground"
            href="https://supabase.com/dashboard/project/_/auth/url-configuration"
          >
            Supabase URL configuration
          </Link>
          .
        </p>
        <ul className="mt-4">
          <li>
            -{" "}
            <span className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-xs font-medium text-secondary-foreground border">
              http://localhost:3000/**
            </span>
          </li>
          {configuredSiteUrl ? (
            <li>
              -{" "}
              <span className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-xs font-medium text-secondary-foreground border">
                {`${configuredSiteUrl}/**`}
              </span>
            </li>
          ) : null}
        </ul>
        {!configuredSiteUrl ? (
          <p className="mt-4">
            Set <code>NEXT_PUBLIC_SITE_URL</code> to show your deployed URL pattern in this guide.
          </p>
        ) : null}
        <Link
          href="https://supabase.com/docs/guides/auth/redirect-urls"
          target="_blank"
          className="text-primary/50 hover:text-primary flex items-center text-sm gap-1 mt-4"
        >
          Redirect URLs Docs <ArrowUpRight size={14} />
        </Link>
      </TutorialStep>
      <TutorialStep title="Sign up your first user">
        <p>
          Head over to the{" "}
          <Link
            href="auth/sign-up"
            className="font-bold hover:underline text-foreground/80"
          >
            Sign up
          </Link>{" "}
          page and sign up your first user. It&apos;s okay if this is just you
          for now. Your awesome idea will have plenty of users later!
        </p>
      </TutorialStep>
    </ol>
  );
}
