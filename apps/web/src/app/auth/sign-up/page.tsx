import { SignUpForm } from "@/components/sign-up-form";

export default function Page() {
  return (
    <div className="flex min-h-svh w-full items-center justify-center bg-[linear-gradient(150deg,#eff8f3_0%,#ffffff_56%,#dbf1e5_100%)] p-6 text-[#0f3f2b] md:p-10">
      <div className="w-full max-w-sm">
        <SignUpForm />
      </div>
    </div>
  );
}
