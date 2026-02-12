"use client";

import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import { validateEmailAddress, validatePasswordValue } from "@/lib/auth-validation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OAuthButtons } from "@/src/components/auth/OAuthButtons";
import { LogoMark } from "@/src/components/brand/LogoMark";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

export function LoginForm({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"div">) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailTouched, setEmailTouched] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const trimmedEmail = useMemo(() => email.trim(), [email]);
  const rawEmailError = useMemo(() => validateEmailAddress(trimmedEmail), [trimmedEmail]);
  const rawPasswordError = useMemo(() => validatePasswordValue(password), [password]);
  const emailError = emailTouched || submitAttempted ? rawEmailError : null;
  const passwordError = passwordTouched || submitAttempted ? rawPasswordError : null;
  const submitDisabled = loading || Boolean(rawEmailError || rawPasswordError);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitAttempted(true);
    setEmailTouched(true);
    setPasswordTouched(true);

    if (rawEmailError || rawPasswordError) {
      return;
    }

    const supabase = createClient();
    setLoading(true);

    try {
      const { error: loginError } = await supabase.auth.signInWithPassword({
        email: trimmedEmail,
        password,
      });

      if (loginError) {
        throw loginError;
      }

      router.push("/dashboard");
    } catch (signInError: unknown) {
      setError(signInError instanceof Error ? signInError.message : "Unable to sign in with email and password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card className="border-blue-200 bg-white text-blue-950">
        <CardHeader>
          <Link href="/" className="inline-flex w-fit items-center gap-2 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#006F34]">
            <LogoMark className="h-6 w-6" />
            <span className="text-sm font-semibold tracking-wide text-[#0B3A27]">Verirule</span>
          </Link>
          <CardTitle className="text-2xl">Sign in</CardTitle>
          <CardDescription className="text-blue-800/80">
            Access your workspace with your registered credentials.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <OAuthButtons mode="login" />
          <div className="my-4 flex items-center gap-2 text-xs text-blue-700/80">
            <span className="h-px flex-1 bg-blue-200" />
            <span>or</span>
            <span className="h-px flex-1 bg-blue-200" />
          </div>
          <form onSubmit={handleLogin} noValidate>
            <div className="flex flex-col gap-5">
              <div className="grid gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@company.com"
                  autoComplete="email"
                  required
                  value={email}
                  onBlur={() => setEmailTouched(true)}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={Boolean(emailError)}
                  className={cn(
                    "border-blue-200 bg-white text-blue-950 placeholder:text-blue-400",
                    emailError ? "border-red-500 focus-visible:ring-red-500" : undefined,
                  )}
                />
                {emailError ? <p className="text-xs text-red-500">{emailError}</p> : null}
              </div>

              <div className="grid gap-2">
                <div className="flex items-center">
                  <Label htmlFor="password">Password</Label>
                  <Link
                    href="/auth/forgot-password"
                    className="ml-auto inline-block text-sm text-blue-700 underline-offset-4 hover:text-blue-900 hover:underline"
                  >
                    Forgot your password?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onBlur={() => setPasswordTouched(true)}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={Boolean(passwordError)}
                  className={cn(
                    "border-blue-200 bg-white text-blue-950 placeholder:text-blue-400",
                    passwordError ? "border-red-500 focus-visible:ring-red-500" : undefined,
                  )}
                />
                {passwordError ? <p className="text-xs text-red-500">{passwordError}</p> : null}
              </div>

              {error ? (
                <p role="alert" className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {error}
                </p>
              ) : null}

              <Button
                type="submit"
                className="relative z-20 w-full bg-blue-700 text-white hover:bg-blue-800 pointer-events-auto"
                disabled={submitDisabled}
              >
                {loading ? "Signing in..." : "Sign in"}
              </Button>
            </div>
            <div className="mt-4 text-center text-sm">
              Don&apos;t have an account?{" "}
              <Link href="/auth/sign-up" className="text-blue-700 underline underline-offset-4 hover:text-blue-900">
                Sign up
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
