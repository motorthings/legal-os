'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { apiGet, apiPost } from '@/lib/api';
import ConfirmModal from '@/components/ConfirmModal';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'user';
  created_at: string;
  avatar_url?: string;
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<'all' | 'admin' | 'user'>('all');
  const [sortBy, setSortBy] = useState<'name' | 'email' | 'created_at'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newUser, setNewUser] = useState({
    email: '',
    name: '',
    role: 'user' as 'admin' | 'user',
  });

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
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const data = await apiGet<{ users: User[] }>('/api/users');
      setUsers(data.users || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await apiPost('/api/users', newUser);

      // Reset form and refresh list
      setNewUser({ email: '', name: '', role: 'user' });
      setShowAddForm(false);
      fetchUsers();

      alert('User created successfully! Invitation email sent.');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create user');
    }
  };

  const handleResendInvitation = (userId: string, userEmail: string) => {
    setConfirmModal({
      open: true,
      title: 'Resend Invitation',
      message: `Resend invitation email to ${userEmail}?`,
      onConfirm: async () => {
        await resendInvitation(userId, userEmail);
      }
    });
  };

  const resendInvitation = async (userId: string, userEmail: string) => {
    try {
      await apiPost(`/api/users/${userId}/resend-invitation`, {});
      alert('Invitation email sent successfully!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to resend invitation');
    }
  };

  const filteredUsers = users
    .filter(user => {
      // Search filter - handle null/undefined name and email
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch =
        (user.name?.toLowerCase().includes(searchLower) ?? false) ||
        (user.email?.toLowerCase().includes(searchLower) ?? false);

      // Role filter
      const matchesRole = roleFilter === 'all' || user.role === roleFilter;

      return matchesSearch && matchesRole;
    })
    .sort((a, b) => {
      // Sorting
      let comparison = 0;
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'email':
          comparison = a.email.localeCompare(b.email);
          break;
        case 'created_at':
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">Loading users...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="heading-1 mb-2">
          User Management
        </h1>
      </div>

      {/* Error Message */}
      {error && (
        <div className="alert alert-error mb-6">
          <p>{error}</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="card p-6">
          <div className="stat-label mb-1">
            Total Users
          </div>
          <div className="stat-number">
            {users.length}
          </div>
        </div>
        <div className="card p-6">
          <div className="stat-label mb-1">
            Admin Users
          </div>
          <div className="stat-number">
            {users.filter(u => u.role === 'admin').length}
          </div>
        </div>
        <div className="card p-6">
          <div className="stat-label mb-1">
            Regular Users
          </div>
          <div className="stat-number">
            {users.filter(u => u.role === 'user').length}
          </div>
        </div>
      </div>

      {/* Search, Filters, and Add Button */}
      <div className="space-y-4 mb-6">
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Search users by name or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-field flex-1"
          />
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="btn-primary"
          >
            {showAddForm ? 'Cancel' : '+ Add User'}
          </button>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <label className="text-sm text-secondary">Role:</label>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value as 'all' | 'admin' | 'user')}
              className="input-field w-32"
            >
              <option value="all">All Roles</option>
              <option value="admin">Admin</option>
              <option value="user">User</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-secondary">Sort By:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'name' | 'email' | 'created_at')}
              className="input-field w-36"
            >
              <option value="created_at">Date Created</option>
              <option value="name">Name</option>
              <option value="email">Email</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm text-secondary">Order:</label>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
              className="input-field w-32"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>

          {/* Clear Filters */}
          {(searchTerm || roleFilter !== 'all' || sortBy !== 'created_at' || sortOrder !== 'desc') && (
            <button
              onClick={() => {
                setSearchTerm('');
                setRoleFilter('all');
                setSortBy('created_at');
                setSortOrder('desc');
              }}
              className="text-sm text-secondary hover:text-primary transition-colors"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Add User Form */}
      {showAddForm && (
        <div className="card mb-6 p-6">
          <h3 className="heading-3 mb-4">
            Add New User
          </h3>
          <form onSubmit={handleAddUser} className="space-y-4">
            <div>
              <label className="label">
                Email
              </label>
              <input
                type="email"
                required
                value={newUser.email}
                onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="label">
                Name
              </label>
              <input
                type="text"
                required
                value={newUser.name}
                onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="label">
                Role
              </label>
              <select
                value={newUser.role}
                onChange={(e) => setNewUser({ ...newUser, role: e.target.value as 'admin' | 'user' })}
                className="input-field"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              type="submit"
              className="btn-primary w-full"
            >
              Create User
            </button>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-page border-b border-default">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                Email
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                Role
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-default">
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-muted">
                  {searchTerm ? 'No users found matching your search' : 'No users yet'}
                </td>
              </tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-hover transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {user.avatar_url ? (
                        <Image
                          src={user.avatar_url}
                          alt={user.name}
                          width={40}
                          height={40}
                          className="h-10 w-10 rounded-full mr-3"
                        />
                      ) : (
                        <div className="avatar-primary h-10 w-10 mr-3">
                          <span className="font-medium">
                            {user.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      )}
                      <div className="font-medium text-primary">
                        {user.name}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-muted">
                    {user.email}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={user.role === 'admin' ? 'badge-primary' : 'badge-secondary'}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-muted">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex gap-2">
                      <Link
                        href={`/admin/users/${user.id}`}
                        className="link font-medium"
                      >
                        View Details
                      </Link>
                      <button
                        onClick={() => handleResendInvitation(user.id, user.email)}
                        className="link font-medium"
                      >
                        Resend Invitation
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Results Count */}
      <div className="mt-4 text-sm text-muted">
        Showing {filteredUsers.length} of {users.length} users
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
