'use client';

import { useState, useEffect, FormEvent, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '@/contexts/AuthContext';
import { apiPut, authenticatedFetch } from '@/lib/api';
import UserMenu from '@/components/UserMenu';
import ConfirmModal from '@/components/ConfirmModal';

export default function ProfilePage() {
  const router = useRouter();
  const { user, profile, signOut, updatePassword } = useAuth();
  const [name, setName] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  // Confirm modal
  const [confirmModal, setConfirmModal] = useState<{
    open: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  }>({
    open: false,
    title: '',
    message: '',
    onConfirm: () => {}
  });

  useEffect(() => {
    if (profile) {
      setName(profile.name);
      setAvatarPreview(profile.avatar_url || null);
    }
  }, [profile]);

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image must be less than 5MB');
      return;
    }

    setError(null);
    setSuccess(null);
    setUploadingAvatar(true);

    try {
      // Create FormData for file upload
      const formData = new FormData();
      formData.append('file', file);

      // Upload avatar
      const response = await authenticatedFetch(
        `/api/users/${profile?.id}/avatar`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to upload avatar');
      }

      const data = await response.json();
      setAvatarPreview(data.avatar_url);
      setSuccess('Avatar updated successfully');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload avatar');
    } finally {
      setUploadingAvatar(false);
    }
  };

  const handleDeleteAvatar = () => {
    setConfirmModal({
      open: true,
      title: 'Remove Profile Picture',
      message: 'Are you sure you want to remove your profile picture?',
      onConfirm: async () => {
        await deleteAvatar();
      }
    });
  };

  const deleteAvatar = async () => {
    setError(null);
    setSuccess(null);
    setUploadingAvatar(true);

    try {
      const response = await authenticatedFetch(
        `/api/users/${profile?.id}/avatar`,
        {
          method: 'DELETE',
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to delete avatar');
      }

      setAvatarPreview(null);
      setSuccess('Avatar removed successfully');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete avatar');
    } finally {
      setUploadingAvatar(false);
    }
  };

  const handleUpdateProfile = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      // Update profile in database
      await apiPut(`/api/users/${profile?.id}`, { name });

      setSuccess('Profile updated successfully');
      setLoading(false);
    } catch (err) {
      setError('Failed to update profile');
      setLoading(false);
    }
  };

  const handleUpdatePassword = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      const { error } = await updatePassword(newPassword);

      if (error) {
        setError(error.message || 'Failed to update password');
        setLoading(false);
        return;
      }

      setSuccess('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setLoading(false);
    } catch (err) {
      setError('An unexpected error occurred');
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    await signOut();
    router.push('/auth/login');
  };

  if (!user || !profile) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const isAdmin = profile?.role === 'admin';
  const getInitials = (name?: string | null) => {
    if (!name) return '?';
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="min-h-screen page-bg">
      {/* Navigation Header */}
      <div className="bg-card flex items-center justify-between px-4 py-3 border-b border-default">
        {/* Hamburger Menu and Profile Avatar */}
        <div className="relative flex items-center gap-3">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-2 hover:bg-hover rounded-md transition-colors"
            aria-label="Menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Profile Avatar (display only) */}
          {profile?.avatar_url ? (
            <Image
              src={profile.avatar_url}
              alt={profile?.name || 'User'}
              width={36}
              height={36}
              className="w-9 h-9 rounded-full object-cover"
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-brand flex items-center justify-center">
              <span className="text-white text-sm font-semibold">
                {getInitials(profile?.name)}
              </span>
            </div>
          )}

          {/* Dropdown Menu */}
          {menuOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setMenuOpen(false)}
              />
              <div className="absolute left-0 top-full mt-2 w-64 bg-card border border-default rounded-lg shadow-lg z-20">
                {/* User Info Section */}
                <div className="px-4 py-4 border-b border-default">
                  <div className="flex items-center gap-3 mb-2">
                    {profile?.avatar_url ? (
                      <Image
                        src={profile.avatar_url}
                        alt={profile?.name || 'User'}
                        width={48}
                        height={48}
                        className="w-12 h-12 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-brand flex items-center justify-center flex-shrink-0">
                        <span className="text-white text-lg font-semibold">
                          {getInitials(profile?.name)}
                        </span>
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-primary truncate">
                        {profile?.name || 'User'}
                      </div>
                      <div className="text-xs text-secondary truncate">
                        {user?.email}
                      </div>
                    </div>
                  </div>
                  {profile?.role && (
                    <div className="inline-flex items-center px-2 py-1 rounded-md bg-accent text-xs font-medium text-brand capitalize">
                      {profile.role}
                    </div>
                  )}
                </div>

                {/* Navigation Section */}
                <div className="py-1">
                  <Link href="/chat" onClick={() => setMenuOpen(false)}>
                    <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                      <span className="text-sm text-primary">Chat</span>
                    </div>
                  </Link>
                  <Link href="/documents" onClick={() => setMenuOpen(false)}>
                    <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                      <span className="text-sm text-primary">Documents</span>
                    </div>
                  </Link>
                </div>

                <div className="border-t border-default"></div>

                {/* Profile & Settings */}
                <div className="py-1">
                  <div className="px-4 py-2 bg-hover">
                    <span className="text-sm text-primary font-medium">Profile Settings</span>
                  </div>
                </div>

                {/* Admin Links */}
                {isAdmin && (
                  <>
                    <div className="border-t border-default"></div>
                    <div className="py-1">
                      <Link href="/admin/users" onClick={() => setMenuOpen(false)}>
                        <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                          <span className="text-sm text-primary">Admin: Users</span>
                        </div>
                      </Link>
                      <Link href="/admin/conversations" onClick={() => setMenuOpen(false)}>
                        <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                          <span className="text-sm text-primary">Admin: Conversations</span>
                        </div>
                      </Link>
                      <Link href="/admin/documents" onClick={() => setMenuOpen(false)}>
                        <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                          <span className="text-sm text-primary">Admin: Documents</span>
                        </div>
                      </Link>
                      <Link href="/admin" onClick={() => setMenuOpen(false)}>
                        <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                          <span className="text-sm text-primary">Admin: Dashboard</span>
                        </div>
                      </Link>
                    </div>
                  </>
                )}

                {/* Sign Out */}
                <div className="border-t border-default"></div>
                <div className="py-1">
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      handleSignOut();
                    }}
                    className="w-full px-4 py-2 hover:bg-hover text-left transition-colors"
                  >
                    <span className="text-sm text-red-600">Sign Out</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Title */}
        <h2 className="heading-2 absolute left-1/2 transform -translate-x-1/2">Contract Review</h2>

        {/* Right side spacer to balance layout */}
        <div className="w-9"></div>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="mb-8">
          <h1 className="heading-1">Profile Settings</h1>
          <p className="text-secondary mt-1">
            Manage your account settings and preferences
          </p>
        </div>

        {/* Success/Error Messages */}
        {success && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4" role="status" aria-live="polite">
            <p className="text-sm text-green-800">{success}</p>
          </div>
        )}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4" role="alert" aria-live="polite">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Profile Information Card */}
        <div className="card p-6 mb-6">
          <h2 className="heading-2 mb-4">
            Profile Information
          </h2>

          {/* Avatar Upload Section */}
          <div className="mb-6 pb-6 divider">
            <label className="label mb-3">
              Profile Picture
            </label>
            <div className="flex items-center gap-4">
              {/* Avatar Preview */}
              <div className="relative">
                {avatarPreview ? (
                  <Image
                    src={avatarPreview}
                    alt="Profile"
                    width={80}
                    height={80}
                    className="w-20 h-20 rounded-full object-cover border-2 border-default"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl font-semibold">
                    {name ? name.charAt(0).toUpperCase() : '?'}
                  </div>
                )}
                {uploadingAvatar && (
                  <div className="absolute inset-0 bg-black bg-opacity-50 rounded-full flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
                  </div>
                )}
              </div>

              {/* Upload Controls */}
              <div className="flex-1">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/jpg,image/png,image/webp"
                  onChange={handleAvatarChange}
                  disabled={uploadingAvatar}
                  className="hidden"
                  id="avatar-upload"
                />
                <div className="flex gap-2">
                  <label
                    htmlFor="avatar-upload"
                    className="cursor-pointer inline-flex items-center px-4 py-2 border border-default rounded-lg text-sm font-medium text-primary bg-white hover:bg-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {avatarPreview ? 'Change Photo' : 'Upload Photo'}
                  </label>
                  {avatarPreview && (
                    <button
                      type="button"
                      onClick={handleDeleteAvatar}
                      disabled={uploadingAvatar}
                      className="inline-flex items-center px-4 py-2 border border-red-200 rounded-lg text-sm font-medium text-red-600 bg-white hover:bg-red-50:bg-red-900 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <p className="text-xs text-muted mt-2">
                  JPG, PNG or WebP. Max 5MB.
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleUpdateProfile} aria-label="Update profile information">
            <div className="space-y-4">
              {/* Email (Read-only) */}
              <div>
                <label className="label">
                  Email
                </label>
                <input
                  type="email"
                  value={user.email || ''}
                  disabled
                  className="input-field cursor-not-allowed"
                />
                <p className="text-xs text-muted mt-1">
                  Email cannot be changed
                </p>
              </div>

              {/* Name */}
              <div>
                <label
                  htmlFor="name"
                  className="label"
                >
                  Name
                </label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={loading}
                  className="input-field disabled:cursor-not-allowed"
                />
              </div>

              {/* Role (Read-only) */}
              <div>
                <label className="label">
                  Role
                </label>
                <input
                  type="text"
                  value={profile.role}
                  disabled
                  className="input-field cursor-not-allowed capitalize"
                />
              </div>

              {/* Client ID (if applicable) */}
              {profile.client_id && (
                <div>
                  <label className="label">
                    Client ID
                  </label>
                  <input
                    type="text"
                    value={profile.client_id}
                    disabled
                    className="input-field cursor-not-allowed font-mono text-sm"
                  />
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-6 btn-primary px-6 py-2 "
              aria-busy={loading}
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </form>
        </div>

        {/* Change Password Card */}
        <div className="card p-6 mb-6">
          <h2 className="heading-2 mb-4">
            Change Password
          </h2>
          <form onSubmit={handleUpdatePassword} aria-label="Change password">
            <div className="space-y-4">
              {/* New Password */}
              <div>
                <label
                  htmlFor="newPassword"
                  className="label"
                >
                  New Password
                </label>
                <input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={loading}
                  className="input-field disabled:cursor-not-allowed"
                  placeholder="••••••••"
                />
                <p className="text-xs text-muted mt-1">
                  Must be at least 6 characters
                </p>
              </div>

              {/* Confirm Password */}
              <div>
                <label
                  htmlFor="confirmPassword"
                  className="label"
                >
                  Confirm New Password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={loading}
                  className="input-field disabled:cursor-not-allowed"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-6 btn-primary px-6 py-2 "
              aria-busy={loading}
            >
              {loading ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>

        {/* Danger Zone */}
        <div className="card border border-red-200 p-6">
          <h2 className="text-xl font-semibold text-red-600 mb-4">
            Danger Zone
          </h2>
          <p className="text-secondary mb-4">
            Once you sign out, you'll need to log in again to access your account.
          </p>
          <button
            onClick={handleSignOut}
            className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Confirm Modal */}
      <ConfirmModal
        open={confirmModal.open}
        title={confirmModal.title}
        message={confirmModal.message}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, open: false })}
      />
    </div>
  );
}
