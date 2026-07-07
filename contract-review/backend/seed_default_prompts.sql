-- Default prompt templates for Wayfinder based on system instructions
-- Run this in Supabase SQL Editor to add default prompts for a user

-- Replace 'YOUR_USER_ID_HERE' with the actual user_id from the users table
-- You can get your user_id by running: SELECT id, email FROM users WHERE email = 'charlie@sickofancy.com';

INSERT INTO user_prompts (user_id, title, prompt_text, display_order) VALUES

-- 1. Signal vs Noise Analyzer
('YOUR_USER_ID_HERE',
 'Signal vs Noise',
 'Help me identify the Signal vs. the Noise in these tasks/projects. Which require my unique expertise and which can be delegated?

[List your tasks/projects here]',
 1),

-- 2. Conceptual Framework Analysis
('YOUR_USER_ID_HERE',
 'Framework Analysis',
 'Analyze this content and determine what conceptual framework would best organize it. Is this project management or learning & development content? What model applies?

[Paste your document or project description here]',
 2),

-- 3. Strategic Document Builder
('YOUR_USER_ID_HERE',
 'Strategic Document',
 'Help me structure a strategic document (SOW, project brief, etc.) with a clear vision. Frame it within an appropriate strategic model.

Document type: [SOW / Brief / etc.]
Target audience: [Who will read this?]
Project/Initiative: [Description]',
 3),

-- 4. Coaching Feedback Draft
('YOUR_USER_ID_HERE',
 'Coaching Feedback',
 'Draft coaching-oriented feedback for a team member. Frame as a development opportunity with coaching questions.

Team member: [Name]
Situation/Work: [What needs feedback?]
Growth area: [What skill are they building?]',
 4),

-- 5. Delegation Opportunity Finder
('YOUR_USER_ID_HERE',
 'Delegation Finder',
 'Help me identify delegation opportunities for this task. Who on the team could own this as a growth opportunity?

Task: [Describe the task]
Skills needed: [List key skills]',
 5);

-- After inserting, verify with:
-- SELECT * FROM user_prompts WHERE user_id = 'YOUR_USER_ID_HERE' ORDER BY display_order;
