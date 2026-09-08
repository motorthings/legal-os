# Evidence Method — how the feed gets fed

**Status:** this document explains how the radar finds evidence, checks it, and decides what is
worth trusting. It is one of three guides: `docs/build-method.md` explains how the work gets made,
`docs/radar-design.md` explains how the engine does its scoring, and this one explains how the
evidence gets collected.
**Owner:** Charlie Fuller. **Last updated:** 2026-09-08.
**Related:** `docs/radar-upgrade-roadmap.md` (what to research next) and the full research notes at
`docs/radar-market-inventory.{md,jsonl}`.

---

## The one-line version

A fact does not get into the radar just because someone found it on the internet. It gets in
because it passed a test. First we search for it from several directions at once. Then three
independent people (well, three AI agents) each try to prove it is wrong. Then we rank it by who
said it. Then we note what kind of change it represents. And if we cannot pin down its date and its
source, we throw it out instead of guessing. What survives is evidence. Everything else is noise.

## The starting idea

Most bad research starts the same way: you find one article, believe it, and build on top of it.
The whole point of this method is to stop doing that. The shift is from *"I found something that
says X"* to *"X held up when three people tried to tear it down."*

Two rules guide everything:

- **Who said it matters more than how many said it.** One hundred blog posts by companies selling
  the tool should not outweigh one court ruling. We weight evidence by who is allowed to make the
  rules, not by who is loudest.
- **"We could not verify it" is a real answer.** It is better to leave a blank than to make up a
  number. A guessed valuation looks impressive and is useless.

---

## The six steps

### 1. Split the question into pieces
Don't shrink the problem. Break it into a few parts that can each be researched at the same time.
For the market research, the parts were: who is funding these companies, what can the AI now do,
what are the rules, how are law firms actually adopting it, and a final part that deliberately
looked for where the whole story might be wrong. That last one is the most important. It is where
fake claims get caught.

### 2. Search in parallel, then read the best sources
Run one search per part, at the same time. Throw out duplicate links. Then open the top sources and
pull out every specific, checkable statement. A statement is only useful if someone could check it
and prove it wrong. A vague marketing slogan that can never be wrong never becomes evidence.

### 3. Try to kill every claim
Take each claim and give it to three independent reviewers, each told to prove it is false. A claim
survives only if at least two of the three cannot break it. This is the step that does the real
work. Across the last several research runs, about 24 of every 25 claims survived, and the one that
got thrown out each time was usually the one that would have embarrassed us: a court rule that only
one source mentioned, a "disqualification" that was actually just a reprimand, a claim about two
companies that no source actually supported.

### 4. Rank it by who said it
When a source first enters the system, we stamp it with a rank and never change it. A court order
or a law is the top rank. A company's own blog is the bottom. A company blog carries about one
hundredth the weight of an ethics opinion from the bar association, and that is on purpose. When a
source is selling the very thing it is talking about, we mark it and count it for less, but we
don't throw it out.

### 5. Note what kind of change it is
Every event gets a label: is it a **continuation** (more of the same), an **origination** (the very
first time something happened), or a **direction shift** (a change of course, like a company buying
its way into a new field)? The label matters because the radar can only predict continuation. More
money into the same area is predictable; the first-ever of something is not. We say so honestly
rather than pretending the radar can see it.

### 6. Refuse to invent
When we cannot pin down a date and an amount for something, the honest answer is "we found
nothing." That is what happened with two companies: they got reported as "no verifiable funding
round this period," not as some made-up number. And the single most valuable finding in the whole
research was itself a nothing: no insurance company has yet required firms to use a certified AI
tool as a condition of coverage. The absence of that event is the thing worth watching.

---

## One more thing: the record is the product

Nothing is thrown away after it is admitted. Every item keeps its date, source, link, rank, and
label, so anyone can trace a score back to the exact item that moved it. We keep two copies of
everything: one written for people (the full research notes) and one written for the computer (the
feed the engine reads). Same information, two formats, nothing invented in the middle.

## The point

The lawyers own the law. The engine owns the scoring. This method owns the evidence. A prediction
is only as good as what it was fed, and what it was fed is only as good as what it was willing to
argue against. The discipline is the whole point: a forecast you can trust is one whose evidence
you can go check yourself.
