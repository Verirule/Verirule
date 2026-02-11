"use client";

import { cn } from "@/lib/utils";
import { createClient } from "@/lib/supabase/client";
import {
  validateEmailAddress,
  validatePasswordConfirmation,
  validatePasswordValue,
} from "@/lib/auth-validation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OAuthButtons } from "@/src/components/auth/OAuthButtons";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

export function SignUpForm({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"div">) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [emailTouched, setEmailTouched] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);
  const [repeatPasswordTouched, setRepeatPasswordTouched] = useState(false);
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const trimmedEmail = useMemo(() => email.trim(), [email]);
  const rawEmailError = useMemo(() => validateEmailAddress(trimmedEmail), [trimmedEmail]);
  const rawPasswordError = useMemo(() => validatePasswordValue(password), [password]);
  const rawRepeatPasswordError = useMemo(
    () => validatePasswordConfirmation(password, repeatPassword),
    [password, repeatPassword],
  );

  const emailError = emailTouched || submitAttempted ? rawEmailError : null;
  const passwordError = passwordTouched || submitAttempted ? rawPasswordError : null;
  const repeatPasswordError = repeatPasswordTouched || submitAttempted ? rawRepeatPasswordError : null;
  const submitDisabled = loading || Boolean(rawEmailError || rawPasswordError || rawRepeatPasswordError);

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setSubmitAttempted(true);
    setEmailTouched(true);
    setPasswordTouched(true);
    setRepeatPasswordTouched(true);

    if (rawEmailError || rawPasswordError || rawRepeatPasswordError) {
      return;
    }

    const supabase = createClient();
    setLoading(true);

    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email: trimmedEmail,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (signUpError) {
        setError(signUpError.message);
        return;
      }

      if (data.session) {
        router.push("/dashboard");
        return;
      }

      setMessage("Check your email to confirm your account. Once confirmed, you can log in.");
    } catch (signUpError: unknown) {
      setError(signUpError instanceof Error ? signUpError.message : "Unable to create your account.");
    } finally {
      setLoading(false);
    }
  };

  const handleResendConfirmation = async () => {
    const resendEmailError = validateEmailAddress(trimmedEmail);
    if (resendEmailError) {
      setError(resendEmailError);
      setEmailTouched(true);
      return;
    }

    const supabase = createClient();
    setLoading(true);
    setError(null);

    try {
      const { error: resendError } = await supabase.auth.resend({
        type: "signup",
        email: trimmedEmail,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        },
      });

      if (resendError) {
        setError(resendError.message);
        return;
      }

      setMessage("If the account exists, a new confirmation email has been sent.");
    } catch (resendError: unknown) {
      setError(resendError instanceof Error ? resendError.message : "Unable to resend confirmation email.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card className="border-blue-200 bg-white text-blue-950">
        <CardHeader>
          <CardTitle className="text-2xl">Create account</CardTitle>
          <CardDescription className="text-blue-800/80">
            Register a workspace account for your compliance team.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <OAuthButtons mode="signup" />
          <div className="my-4 flex items-center gap-2 text-xs text-blue-700/80">
            <span className="h-px flex-1 bg-blue-200" />
            <span>or</span>
            <span className="h-px flex-1 bg-blue-200" />
          </div>
          <form onSubmit={handleSignUp} noValidate>
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
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={password}
                  onBlur={() => setPasswordTouched(true)}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={Boolean(passwordError)}
                  className={cn(
                    "border-blue-200 bg-white text-blue-950 placeholder:text-blue-400",
                    passwordError ? "border-red-500 focus-visible:ring-red-500" : undefined,
                  )}
                />
                {passwordError ? (
                  <p className="text-xs text-red-500">{passwordError}</p>
                ) : (
                  <p className="text-xs text-blue-700/80">Use at least 8 characters.</p>
                )}
              </div>

              <div className="grid gap-2">
                <Label htmlFor="repeat-password">Repeat Password</Label>
                <Input
                  id="repeat-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={repeatPassword}
                  onBlur={() => setRepeatPasswordTouched(true)}
                  onChange={(e) => setRepeatPassword(e.target.value)}
                  aria-invalid={Boolean(repeatPasswordError)}
                  className={cn(
                    "border-blue-200 bg-white text-blue-950 placeholder:text-blue-400",
                    repeatPasswordError ? "border-red-500 focus-visible:ring-red-500" : undefined,
                  )}
                />
                {repeatPasswordError ? <p className="text-xs text-red-500">{repeatPasswordError}</p> : null}
              </div>

              {error ? (
                <div
                  role="alert"
                  className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200"
                >
                  {error}
                </div>
              ) : null}

              {message ? (
                <div
                  aria-live="polite"
                  className="rounded-md border border-blue-300 bg-blue-50 px-3 py-2 text-sm text-blue-800 dark:border-blue-900/60 dark:bg-blue-950/40 dark:text-blue-200"
                >
                  {message}
                </div>
              ) : null}

              <Button
                type="submit"
                className="relative z-20 w-full bg-blue-700 text-white hover:bg-blue-800 pointer-events-auto"
                disabled={submitDisabled}
              >
                {loading ? "Creating account..." : "Create account"}
              </Button>

              {message && trimmedEmail ? (
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled={loading}
                  onClick={handleResendConfirmation}
                >
                  {loading ? "Resending..." : "Resend confirmation email"}
                </Button>
              ) : null}
            </div>
            <div className="mt-4 text-center text-sm">
              Already have an account?{" "}
              <Link href="/auth/login" className="text-blue-700 underline underline-offset-4 hover:text-blue-900">
                Sign in
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
