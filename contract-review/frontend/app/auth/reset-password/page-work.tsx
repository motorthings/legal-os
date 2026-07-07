'use client';

import { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabase';

export default function ResetPasswordPage() {
  const router = useRouter();
  const { updatePassword } = useAuth();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);

  // Handle the URL hash parameters from the password reset email
  useEffect(() => {
    const handlePasswordReset = async () => {
      try {
        // Check if we have hash parameters (recovery tokens from email)
        const hash = window.location.hash;

        if (hash) {
          // Parse the hash parameters
          const params = new URLSearchParams(hash.substring(1));
          const access_token = params.get('access_token');
          const refresh_token = params.get('refresh_token');
          const type = params.get('type');

          if (access_token && type === 'recovery') {
            // Set the session using the tokens from the URL
            const { data, error: sessionError } = await supabase.auth.setSession({
              access_token,
              refresh_token: refresh_token || ''
            });

            if (sessionError) {
              console.error('Session error:', sessionError);
              setError('Invalid or expired reset link. Please request a new one.');
              return;
            }

            if (data.session) {
              setSessionReady(true);
              // Clear the hash from URL for security
              window.history.replaceState(null, '', window.location.pathname);
            }
          } else {
            setError('Invalid password reset link. Please request a new one.');
          }
        } else {
          // No hash parameters - user might have navigated here directly
          setError('Please use the password reset link sent to your email.');
        }
      } catch (err) {
        console.error('Error handling password reset:', err);
        setError('An error occurred. Please try again.');
      }
    };

    handlePasswordReset();
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    // Check if session is ready
    if (!sessionReady) {
      setError('Please wait for the session to be established');
      return;
    }

    // Validation
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      const { error } = await updatePassword(password);

      if (error) {
        setError(error.message || 'Failed to update password');
        setLoading(false);
        return;
      }

      setSuccess(true);

      // Redirect to login after 2 seconds
      setTimeout(() => {
        router.push('/auth/login');
      }, 2000);
    } catch (err) {
      setError('An unexpected error occurred');
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center page-bg px-4">
        <div className="max-w-md w-full">
          <div className="card p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h2 className="heading-2 mb-2">
              Password Updated!
            </h2>
            <p className="text-secondary mb-4">
              Your password has been successfully updated.
            </p>
            <p className="text-sm text-secondary">Redirecting...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show loading state while establishing session
  if (!sessionReady && !error) {
    return (
      <div className="min-h-screen flex items-center justify-center page-bg px-4">
        <div className="max-w-md w-full">
          <div className="card p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-secondary">Verifying your reset link...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center page-bg px-4">
      <div className="max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-primary mb-2">
            Contract Review
          </h1>
          <p className="text-secondary">Set your new password</p>
        </div>

        {/* Reset Form */}
        <div className="card p-8">
          <form onSubmit={handleSubmit}>
            {/* Error Message */}
            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            {/* Password Field */}
            <div className="mb-4">
              <label htmlFor="password" className="label">
                New Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                className="input-field"
                placeholder="••••••••"
              />
              <p className="text-xs text-muted mt-1">
                Must be at least 6 characters
              </p>
            </div>

            {/* Confirm Password Field */}
            <div className="mb-6">
              <label htmlFor="confirmPassword" className="label">
                Confirm New Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                className="input-field"
                placeholder="••••••••"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-2.5"
            >
              {loading ? 'Updating...' : 'Update Password'}
            </button>
          </form>

          {/* Back to Login */}
          <div className="mt-6 text-center">
            <Link href="/auth/login" className="text-sm link font-medium">
              ← Back to login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
