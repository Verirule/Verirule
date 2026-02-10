const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const minimumPasswordLength = 8;

export function validateEmailAddress(value: string): string | null {
  const trimmed = value.trim();

  if (!trimmed) {
    return "Email is required.";
  }

  if (!emailPattern.test(trimmed)) {
    return "Enter a valid email address.";
  }

  return null;
}

export function validatePasswordValue(value: string): string | null {
  if (!value) {
    return "Password is required.";
  }

  if (value.length < minimumPasswordLength) {
    return `Password must be at least ${minimumPasswordLength} characters.`;
  }

  return null;
}

export function validatePasswordConfirmation(password: string, repeatPassword: string): string | null {
  if (!repeatPassword) {
    return "Repeat password is required.";
  }

  if (password !== repeatPassword) {
    return "Passwords do not match.";
  }

  return null;
}
