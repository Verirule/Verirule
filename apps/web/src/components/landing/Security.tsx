const controls = [
  {
    title: "Row-level security (RLS)",
    description: "Tenant isolation is enforced in the data layer to reduce cross-org access risk.",
  },
  {
    title: "JWT verification on API",
    description: "Backend endpoints validate Supabase bearer tokens through JWKS before returning data.",
  },
  {
    title: "Secrets never in client",
    description: "Sensitive integration values stay server-side and are not exposed to browser code.",
  },
  {
    title: "Rate limiting + audit logging",
    description: "Baseline controls are in place today and are actively being expanded.",
  },
];

export function Security() {
  return (
    <div className="rounded-2xl border bg-card/80 p-6 sm:p-8">
      <div className="grid gap-4 md:grid-cols-2">
        {controls.map((item) => (
          <article key={item.title} className="rounded-xl border bg-background/80 p-4">
            <h3 className="text-sm font-semibold">{item.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
