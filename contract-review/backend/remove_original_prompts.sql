-- Remove the 5 original prompts (keeping only the Wayfinder prompts)
-- Run this in Supabase SQL Editor

DELETE FROM user_prompts
WHERE user_id = 'd3ba5354-873a-435a-a36a-853373c4f6e5'
AND title IN (
    'Weekly Status Update',
    'Summarize Email',
    'Meeting Prep',
    'Draft Response',
    'Research Summary'
);

-- Verify deletion - should show only 5 Wayfinder prompts remaining
SELECT title, display_order
FROM user_prompts
WHERE user_id = 'd3ba5354-873a-435a-a36a-853373c4f6e5'
ORDER BY display_order;
