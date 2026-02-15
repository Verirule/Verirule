import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Page() {
  return (
    <div className="flex min-h-svh w-full items-center justify-center bg-white p-6 text-blue-950 md:p-10">
      <div className="w-full max-w-sm">
        <div className="flex flex-col gap-6">
          <Card className="border-blue-200 bg-white text-blue-950">
            <CardHeader>
              <CardTitle className="text-2xl">Account verification required</CardTitle>
              <CardDescription className="text-blue-800/80">Check your inbox for the verification link</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-blue-900/80">
                Before signing in, confirm your account from the verification email sent during registration.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

