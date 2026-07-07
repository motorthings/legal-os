-- Update user role to enable admin features
-- Run this in Supabase SQL Editor

-- First, check your current role:
SELECT id, email, role FROM users WHERE email = 'charlie@sickofancy.com';

-- Update your role to 'admin' (gives full access):
UPDATE users
SET role = 'admin'
WHERE email = 'charlie@sickofancy.com';

-- Verify the update:
SELECT id, email, role FROM users WHERE email = 'charlie@sickofancy.com';

-- Alternative: If you want 'client_admin' role instead (can manage clients but not all admin features):
-- UPDATE users SET role = 'client_admin' WHERE email = 'charlie@sickofancy.com';

-- Available roles:
-- 'user' - Regular user, can use chat but can't delete conversations
-- 'client_admin' - Can manage their client's data and delete conversations
-- 'admin' - Full admin access
