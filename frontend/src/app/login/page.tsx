"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { signIn, signUp, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    router.push("/");
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const result =
      mode === "login"
        ? await signIn(email, password)
        : await signUp(email, password, name);

    if (result.error) {
      setError(result.error);
    } else if (mode === "signup") {
      setError("Check your email for a confirmation link.");
    } else {
      router.push("/");
    }
    setLoading(false);
  }

  return (
    <div className="max-w-md mx-auto mt-16">
      <div className="card p-8">
        <h1 className="text-2xl font-bold mb-6">
          {mode === "login" ? "Sign In" : "Create Account"}
        </h1>

        {error && (
          <div
            className={`mb-4 p-3 rounded-lg text-sm ${
              error.includes("Check your email")
                ? "bg-[var(--metric-dim)] text-[var(--metric)]"
                : "bg-[var(--rose-dim)] text-[var(--rose)]"
            }`}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid gap-4">
          {mode === "signup" && (
            <div>
              <label className="block font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-1">
                Name
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                required
              />
            </div>
          )}
          <div>
            <label className="block font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@firm.com"
              required
            />
          </div>
          <div>
            <label className="block font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-dim)] mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={6}
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading
              ? "Loading..."
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>

        <div className="mt-4 text-sm text-center text-[var(--text-dim)]">
          {mode === "login" ? (
            <>
              No account?{" "}
              <button
                onClick={() => setMode("signup")}
                className="text-[var(--secondary)] hover:underline bg-transparent border-0 cursor-pointer"
              >
                Create one
              </button>
            </>
          ) : (
            <>
              Have an account?{" "}
              <button
                onClick={() => setMode("login")}
                className="text-[var(--secondary)] hover:underline bg-transparent border-0 cursor-pointer"
              >
                Sign in
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
