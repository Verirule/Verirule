import { cn } from "@/lib/utils";

type SocialIconsProps = {
  className?: string;
  iconClassName?: string;
};

const links = [
  {
    name: "LinkedIn",
    href: "https://www.linkedin.com/company/verirule",
    path: "M6.94 8.5H3.56V20h3.38V8.5ZM5.25 3A1.96 1.96 0 1 0 5.25 6.92 1.96 1.96 0 0 0 5.25 3ZM20.44 13.42c0-3.07-1.64-4.5-3.83-4.5-1.77 0-2.56.98-3 1.66V8.5h-3.38V20h3.38v-6.38c0-1.68.32-3.31 2.4-3.31 2.06 0 2.08 1.93 2.08 3.42V20h3.35v-6.58Z",
  },
  {
    name: "X",
    href: "https://x.com/verirule",
    path: "M18.901 1.153h3.68l-8.04 9.19L24 22.847h-7.406l-5.8-7.584-6.64 7.584H.474l8.6-9.83L0 1.153h7.594l5.243 6.932 6.064-6.932Zm-1.29 19.471h2.039L6.486 3.257H4.298Z",
  },
  {
    name: "GitHub",
    href: "https://github.com/Verirule",
    path: "M12 2C6.477 2 2 6.484 2 12.017c0 4.426 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.009-.868-.014-1.703-2.782.605-3.369-1.343-3.369-1.343-.455-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.004.07 1.532 1.032 1.532 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.094.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844c.85.004 1.705.114 2.504.337 1.909-1.296 2.747-1.026 2.747-1.026.546 1.379.203 2.398.1 2.651.64.7 1.028 1.594 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.919.678 1.852 0 1.336-.012 2.414-.012 2.743 0 .268.18.58.688.482A10.019 10.019 0 0 0 22 12.017C22 6.484 17.522 2 12 2Z",
  },
] as const;

export function SocialIcons({ className, iconClassName }: SocialIconsProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      {links.map((item) => (
        <a
          key={item.name}
          href={item.href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={item.name}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 text-slate-300 transition-colors hover:border-slate-500 hover:text-white"
        >
          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
            fill="currentColor"
            className={cn("h-4 w-4", iconClassName)}
          >
            <path d={item.path} />
          </svg>
        </a>
      ))}
    </div>
  );
}
