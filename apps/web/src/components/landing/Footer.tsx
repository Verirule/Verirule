export function Footer() {
  return (
    <footer className="border-t border-border/70 py-10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 text-sm text-muted-foreground sm:px-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <a href="https://discord.gg/" target="_blank" rel="noreferrer" className="transition-colors hover:text-foreground">
            Discord
          </a>
          <a
            href="https://x.com/verirule"
            target="_blank"
            rel="noreferrer"
            className="transition-colors hover:text-foreground"
          >
            X
          </a>
        </div>
        <p>Licensed under MIT. Copyright 2026 Verirule.</p>
      </div>
    </footer>
  );
}
