# Prompt Engineering for Lawyers

A practical guide. Not theory. What to type, what not to type.

---

## The Golden Rule

**AI output is a first draft. Your judgment is the final draft.** Never submit, file, or send AI output without review. You are responsible for every word that leaves your name.

---

## The Five Rules of Legal Prompting

### 1. Give It a Role

Bad: "Review this contract."
Good: "You are a senior M&A associate at a global law firm. Review this asset purchase agreement for a private equity buyer acquiring a manufacturing target. Flag anything that disadvantages the buyer."

The role sets the lens. An employment lawyer reads a contract differently than an M&A lawyer. Tell it which lens to use.

### 2. Give It the Standard

Bad: "Is this clause risky?"
Good: "Compare this indemnification clause against the firm's standard position: mutual indemnification, carveout for third-party IP claims, cap at fees paid. Flag every deviation."

Don't ask for open-ended judgment. Give it a yardstick.

### 3. Tell It What You Don't Want

Bad: "Summarize this deposition."
Good: "Summarize this deposition, focusing only on admissions that contradict the witness's prior written statement. Skip procedural exchanges, objections, and background testimony."

The model will fill space if you let it. Constrain the output.

### 4. Ask It to Show Its Work

Bad: "Is this contract assignable?"
Good: "Find every clause in this contract that relates to assignment, change of control, or transfer. Quote the specific language. Then tell me whether the contract is assignable without consent, and explain your reasoning step by step."

Chain-of-reasoning prompts produce more reliable outputs. You can check the reasoning. You can't check a black-box answer.

### 5. Break Complex Tasks Into Steps

Bad: "Review this 200-page credit agreement and tell me everything that's wrong."
Good: "Step 1: Extract all financial covenants. Step 2: Compare each against standard market terms for a $500M senior secured facility. Step 3: Flag any covenant that is unusually tight or unusually loose. Step 4: Identify any missing covenants that should be present. Now execute each step in order."

One prompt = one task. Chain them for complex work.

---

## What NOT to Put in a Prompt

### Never include:
- Client names, matter numbers, or any identifying information
- Full contracts or documents (unless using a firm-approved tool with ZDR)
- Personal data about employees, counterparties, or individuals
- Confidential deal terms, valuations, or strategy
- Anything you wouldn't put in an unencrypted email

### In governed firm tools (Harvey, internal tools):
- Firm tools have zero data retention. Inputs are purged after response generation.
- Still: minimize. If you only need a clause, paste the clause, not the whole contract.

### In consumer tools (ChatGPT, Claude personal, Gemini):
- Never. These tools may use your input for training. Pasting client data into consumer AI is a confidentiality breach.

---

## Prompt Templates by Task

### Summarize a Document
```
You are a [practice area] attorney. Summarize this [document type] for a [partner/client/briefing].
Focus on: [3-5 specific things to look for].
Omit: [what to skip].
Format: [bullet points / paragraphs / table].
```

### Extract Clauses
```
Extract every [clause type] from the following contract.
For each clause found:
- Quote the operative language verbatim
- Note the section number
- Compare against: [standard position]
- Flag: [specific concern]
```

### Draft a First Draft
```
You are a [practice area] attorney drafting a [document type] for [client type] in [jurisdiction].
Context: [2-3 sentences about the matter].
Include: [specific provisions required].
Exclude: [what's not relevant].
Tone: [formal / client-facing / internal memo].
Jurisdiction: [state/country]. Use [state/country] law and terminology.
```

### Compare Documents
```
Compare Document A (dated [date]) against Document B (dated [date]).
Identify every difference. Group changes into:
1. Substantive changes (alter rights, obligations, or risk)
2. Language changes (different words, same meaning)
3. New additions (in Document B but not A)
4. Deletions (in Document A but not B)
For each substantive change, note whether it favors the [buyer/seller/employer/employee].
```

### Legal Research (Governed Tools Only)
```
Research question: [specific legal question].
Jurisdiction: [state/country].
Find: cases, statutes, and regulations that address this question.
For each source: provide the citation, the key holding, and whether it supports or contradicts [position].
Flag: any contrary authority that should be addressed.
```
**Warning:** Always verify citations. AI can fabricate case names, docket numbers, and holdings that look completely real.

---

## The Feedback Loop

The tool gets better when you tell it what it got wrong.

If an output was:
- **Correct and useful**: Note what worked. The pattern gets reinforced.
- **Partially correct**: Flag the specific error. "The indemnification analysis was right, but you missed the carveout in section 8.3."
- **Wrong**: Report it. Every error report makes the system better for everyone.

Report issues through: [feedback channel to be configured per firm]
