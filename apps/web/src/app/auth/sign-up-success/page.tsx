import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Page() {
  return (
    <div className="flex min-h-svh w-full items-center justify-center bg-[#081326] p-6 text-slate-100 md:p-10">
      <div className="w-full max-w-sm">
        <div className="flex flex-col gap-6">
          <Card className="border-slate-800 bg-slate-900/90 text-slate-100">
            <CardHeader>
              <CardTitle className="text-2xl">Account verification required</CardTitle>
              <CardDescription className="text-slate-300">Check your inbox for the verification link</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-300">
                Before signing in, confirm your account from the verification email sent during registration.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
