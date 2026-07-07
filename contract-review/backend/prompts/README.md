# Solomon Pipeline Prompts

This directory contains the prompt templates used by the Solomon pipeline for converting interview transcripts into personalized system instructions.

## Files

### `solomon_stage2_customization.txt`
**Used by:** `services/solomon_stage2.py`
**Purpose:** Template customization instructions for Claude Opus

This prompt guides Claude Opus in customizing the base XML template (`system_instructions/default.txt`) with client-specific data extracted from Stage 1.

**What it customizes:**
1. `<configuration>` block - Client name, role, organization, assistant name
2. `<role>` section - Leadership styles and core values
3. `<context>` section - Organization type, role, pain points
4. Voice & Tone criterion - Communication style preferences
5. `<interaction_guidelines>` - Style description
6. Signal_Analyzer examples - Domain-relevant activation prompts
7. Conceptual_Modeler examples - Industry-specific frameworks

**What it preserves:**
- All XML structure and tags
- All 5 Core Functions definitions
- All guardrails and safety mechanisms
- All evaluation criteria
- Process workflows and creation principles

## Editing Guidelines

When editing these prompts:

1. **Test changes thoroughly** - Run `test_synthetic_interview.py` after modifications
2. **Preserve placeholders** - Maintain `{template}`, `{extraction_json}`, `{client_name}`, etc.
3. **Version control** - These prompts are critical infrastructure; document changes in commits
4. **Backward compatibility** - Ensure changes work with existing extraction JSON structure

## Related Files

- **Template:** `system_instructions/default.txt` - The base XML template
- **Stage 1 Code:** `services/solomon_stage1.py` - Extraction logic
- **Stage 2 Code:** `services/solomon_stage2.py` - Loads and uses these prompts
- **Documentation:** `system_instructions/Solomon_Translation_Method.md`
