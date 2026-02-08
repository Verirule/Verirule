import Layout from "../components/Layout";

export default function HomePage() {
  return (
    <Layout>
      <main className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid gap-8 md:grid-cols-2 md:items-center">
          <div>
            <h1 className="text-3xl font-semibold text-brand-900 sm:text-4xl">
              Verirule
            </h1>
            <p className="mt-3 text-brand-700">
              Automated regulatory compliance monitoring
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <a
                className="rounded-md bg-brand-900 px-4 py-2 text-sm text-white"
                href="/login"
              >
                Get Started
              </a>
              <a
                className="rounded-md border border-brand-100 px-4 py-2 text-sm text-brand-900"
                href="/login"
              >
                Sign In
              </a>
            </div>
          </div>
          <div className="rounded-lg border border-brand-100 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <img
                src="/branding/logo-mark.svg"
                alt="Verirule"
                className="h-10 w-10"
              />
              <div>
                <p className="text-sm text-brand-700">Compliance status</p>
                <p className="text-lg font-semibold text-brand-900">All systems aligned</p>
              </div>
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-md border border-brand-100 p-3">
                <p className="text-xs text-brand-700">Policy checks</p>
                <p className="text-lg font-semibold text-brand-900">128</p>
              </div>
              <div className="rounded-md border border-brand-100 p-3">
                <p className="text-xs text-brand-700">Alerts resolved</p>
                <p className="text-lg font-semibold text-brand-900">42</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </Layout>
  );
}
