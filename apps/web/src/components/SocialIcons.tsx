import { cn } from "@/lib/utils";

type SocialIconsProps = {
  className?: string;
  iconClassName?: string;
};

const links = [
  {
    name: "X",
    href: "https://x.com/verirule",
    icon: (
      <path d="M18.9 2H21l-6.5 7.44L22 22h-5.88l-4.6-6.02L6.2 22H4.1l6.95-7.94L2 2h6.03l4.16 5.5L18.9 2Zm-2.06 18h1.16L7.4 3.9H6.15L16.84 20Z" />
    ),
  },
  {
    name: "Discord",
    href: "https://discord.gg/",
    icon: (
      <path d="M20.32 4.37A18.34 18.34 0 0 0 15.77 3l-.22.45c1.76.44 2.57 1.07 3.28 1.7a14.2 14.2 0 0 0-4.53-1.4 15.4 15.4 0 0 0-4.6 0A14.2 14.2 0 0 0 5.17 5.2c.7-.63 1.5-1.26 3.27-1.7L8.22 3a18.34 18.34 0 0 0-4.55 1.37C.79 8.72.03 12.96.4 17.14A18.5 18.5 0 0 0 5.98 20l1.2-1.65c-.68-.24-1.32-.54-1.93-.9.16.11.34.2.51.29 3.26 1.5 6.8 1.5 10.03 0 .17-.09.35-.18.51-.3-.61.37-1.25.67-1.93.91l1.2 1.65a18.48 18.48 0 0 0 5.58-2.86c.44-4.86-.74-9.07-3.83-12.77ZM8.66 14.7c-1.07 0-1.94-.98-1.94-2.18 0-1.2.86-2.18 1.94-2.18 1.08 0 1.96.98 1.94 2.18 0 1.2-.87 2.18-1.94 2.18Zm6.68 0c-1.08 0-1.95-.98-1.94-2.18 0-1.2.86-2.18 1.94-2.18 1.08 0 1.96.98 1.94 2.18 0 1.2-.86 2.18-1.94 2.18Z" />
    ),
  },
  {
    name: "GitHub",
    href: "https://github.com/Verirule",
    icon: (
      <path d="M12 2C6.48 2 2 6.58 2 12.25c0 4.53 2.87 8.37 6.84 9.72.5.1.66-.21.66-.48v-1.72c-2.78.62-3.36-1.21-3.36-1.21-.45-1.18-1.11-1.5-1.11-1.5-.9-.62.07-.61.07-.61 1 .07 1.52 1.04 1.52 1.04.88 1.55 2.31 1.1 2.87.84.09-.66.34-1.1.63-1.36-2.22-.26-4.56-1.14-4.56-5.05 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.33.1-2.74 0 0 .84-.28 2.76 1.05A9.5 9.5 0 0 1 12 7.66a9.5 9.5 0 0 1 2.5.35c1.92-1.33 2.76-1.05 2.76-1.05.55 1.41.2 2.48.1 2.74.64.72 1.03 1.63 1.03 2.75 0 3.92-2.35 4.8-4.58 5.05.36.31.68.95.68 1.91v2.83c0 .27.16.58.67.48A10.2 10.2 0 0 0 22 12.25C22 6.58 17.52 2 12 2Z" />
    ),
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
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 text-slate-300 transition-colors hover:border-sky-400 hover:text-sky-300"
        >
          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
            fill="currentColor"
            className={cn("h-4 w-4", iconClassName)}
          >
            {item.icon}
          </svg>
        </a>
      ))}
    </div>
  );
}
