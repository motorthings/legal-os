# Default Prompt Templates

This directory contains SQL scripts to seed default prompt templates for users.

## Adding Default Prompts for Wayfinder

The `seed_default_prompts.sql` file contains 5 default prompts based on the Wayfinder system instructions:

1. **Signal vs Noise** - Analyze tasks to identify what requires unique expertise vs delegation
2. **Framework Analysis** - Determine appropriate conceptual frameworks for content
3. **Strategic Document** - Structure SOWs and project briefs with clear vision
4. **Coaching Feedback** - Draft development-oriented feedback for team members
5. **Delegation Finder** - Identify delegation opportunities aligned with team growth

### How to Use

**Step 1: Get your user ID**
```sql
SELECT id, email FROM users WHERE email = 'charlie@sickofancy.com';
```
Copy the `id` value.

**Step 2: Add default prompts**
1. Open `seed_default_prompts.sql`
2. Replace all instances of `'YOUR_USER_ID_HERE'` with your actual user ID from Step 1
3. Run the modified script in Supabase SQL Editor

**Step 3: Verify**
```sql
SELECT * FROM user_prompts WHERE user_id = 'YOUR_USER_ID' ORDER BY display_order;
```

You should see 5 prompts for the user.

### Customizing Prompts

After seeding, you can:
- Edit prompts via the admin dashboard
- Add more prompts as needed
- Reorder prompts by changing the `display_order` value
- Delete prompts that aren't useful

### Prompt Structure

Each prompt has:
- `title` - Short name shown in the sidebar
- `prompt_text` - The actual prompt template with [placeholder] instructions
- `display_order` - Controls the order shown in the sidebar (lower = higher in list)
