import Navbar from "../components/Navbar";

export default function HomePage() {
  return (
    <div>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-12">
        <h1 className="text-3xl font-semibold text-brand-900">Verirule</h1>
        <p className="mt-3 text-brand-700">
          Automated regulatory compliance monitoring
        </p>
      </main>
    </div>
  );
}
