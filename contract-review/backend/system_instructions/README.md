# System Instructions - Per-User Configuration

This directory contains system instructions (system prompts) for the AI assistant. Instructions are customized per-user and managed via GitHub.

## Directory Structure

```
system_instructions/
├── README.md              # This file
├── default.txt            # Default/fallback template (used when no user-specific file exists)
└── users/
    ├── {user_id_1}.txt    # User 1's custom instructions
    ├── {user_id_2}.txt    # User 2's custom instructions
    └── ...
```

## How It Works

1. **Per-User Instructions**: Each user can have their own custom system instructions stored in `users/{user_id}.txt`

2. **Fallback to Default**: If a user-specific file doesn't exist, the system loads `default.txt`

3. **Template Variables**: All instructions support template variables that are automatically replaced at runtime

## Template Variables

Use these variables in your system instructions - they'll be replaced with actual values at runtime:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `{user_name}` | User's full name | "John Doe" |
| `{user_email}` | User's email address | "john@example.com" |
| `{user_role}` | User's role | "admin", "client_admin", or "user" |
| `{client_name}` | Client organization name | "Acme Corporation" |
| `{client_id}` | Client UUID | "123e4567-e89b-12d3-a456-426614174000" |
| `{assistant_name}` | Custom assistant name | "MitCH", "SuperAssistant", etc. |

### Example Usage:

```
You are {assistant_name}, an AI assistant for {user_name} at {client_name}.

The user's role is {user_role}, so you should tailor your responses accordingly.
```

Will become:

```
You are MitCH, an AI assistant for John Doe at Acme Corporation.

The user's role is admin, so you should tailor your responses accordingly.
```

## Creating User-Specific Instructions

### Method 1: GitHub Direct Edit (Recommended)

1. Navigate to `backend/system_instructions/users/` in GitHub
2. Click "Add file" → "Create new file"
3. Name it `{user_id}.txt` (get the user ID from the Supabase users table)
4. Paste your system instructions (you can use template variables)
5. Commit the file
6. Railway will auto-deploy and pick up the new instructions on next server restart

### Method 2: Local Development

1. Create a file: `backend/system_instructions/users/{user_id}.txt`
2. Add your system instructions with template variables
3. Test locally
4. Commit and push to GitHub
5. Railway auto-deploys

## Finding a User's ID

To get a user's UUID for naming their instruction file:

1. **Via Supabase Dashboard**:
   - Go to Supabase → Table Editor → `users` table
   - Find the user by email
   - Copy their `id` (UUID format)

2. **Via Admin Panel**:
   - Log in to admin account
   - Go to Clients → Select client → Users
   - The user ID will be visible in the URL when viewing user details

## Updating Default Instructions

The `default.txt` file serves as the fallback for all users who don't have custom instructions.

To update:
1. Edit `backend/system_instructions/default.txt` in GitHub
2. Commit the changes
3. Railway auto-deploys
4. New default applies to all users without custom instructions

## Template Format Guidelines

### Good Practices:

✅ Use clear, specific instructions
✅ Include template variables for personalization
✅ Structure with clear sections
✅ Define the assistant's role and capabilities
✅ Set boundaries and limitations

### Example Structure:

```
You are {assistant_name}, an AI executive assistant for {user_name} at {client_name}.

## Your Role
[Define what the assistant does]

## Capabilities
- Capability 1
- Capability 2

## Interaction Guidelines
- Guideline 1
- Guideline 2

## Limitations
- What you cannot do
```

## Testing Instructions

To test system instructions locally:

```bash
cd backend
python system_instructions_loader.py
```

This will:
- Load the default instructions
- Test template variable replacement
- Verify file structure

## Deployment

**Automatic Deployment**:
- Any commit to `main` branch triggers Railway deployment
- Server restart picks up new/modified instruction files
- No manual deployment needed

**Note**: Changes to system instructions require a server restart to take effect. Railway handles this automatically on deployment.

## Troubleshooting

### Issue: User not getting custom instructions
**Solution**:
- Verify file name matches user UUID exactly: `users/{user_id}.txt`
- Check Railway logs for file loading messages
- Ensure file is committed to GitHub `main` branch

### Issue: Template variables not replaced
**Solution**:
- Verify variable names match exactly (case-sensitive)
- Check Railway logs for loading messages
- Ensure using curly braces: `{user_name}` not `$user_name`

### Issue: Instructions not updating
**Solution**:
- Commit changes to GitHub
- Wait for Railway auto-deployment (~30 seconds)
- Server must restart to load new files

## Security Notes

- System instructions are server-side only - users never see them
- Instructions files are NOT exposed via API
- Only server-side code can read these files
- Version controlled via GitHub for audit trail

---

**Last Updated**: November 3, 2025
**System**: Per-user system instructions with template variables
