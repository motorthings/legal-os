'use client';

import { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { X } from 'lucide-react';

// A static, one-page explainer of how the simulation works — the same for every run.
// It answers the only three questions a partner needs to trust the result: where the
// starting point comes from, how the plan is chosen, and how we know it holds. Kept out
// of the report itself on purpose, so the report stays about *your firm*, not the machine.
const HOW_IT_WORKS = `
## How this works

You don't have to trust a black box. Here is the whole method, in three steps.

### 1. We build your firm, then let it run.

We don't start from a formula. We stand up a working model of your firm — the partners,
the associates, the AI tools already in the building — and let them work real matters,
quarter after quarter, for several years.

Every quarter, drafts get written and reviewed, hand-offs succeed or fail, clients pay
early or late, people stay or leave. The profit that falls out of all that motion is your
**baseline**. Nobody typed it in. It's what your firm produces when it runs exactly as it
does today.

That's why the baseline should look familiar. If it doesn't, the model is wrong, and the
report tells you where to check.

### 2. We test every change — alone, then together.

There are five moves on the table: how you bill, how work is handed off, how you pay for
AI adoption, how fast you act on results, and how flat the pyramid is.

We try each one on its own, then in combinations, rerunning the entire firm each time. A
change that only looks good on paper falls apart here, because it has to survive the same
rework and write-offs as everything else. We keep the combination that lifts profit the
most — and we note the **order**, because some moves only pay off after another one clears
the way. That's the **recommendation**.

### 3. We run the winning plan again and again to see if it holds.

One good result can be luck. So we take the recommended plan and run it across dozens of
fresh scenarios — the same firm, but different rolls of the dice on which matters land,
which hand-offs break, and who walks out the door.

If the plan comes out ahead in nearly all of them, it's real, and we say so. If it only
wins on average, we tell you to trust the direction but treat the dollar figure as
provisional. That's the difference between a forecast and a stress test. **This is the
stress test.**

---

**What to trust.** The direction and the order are solid — they come from running your
firm thousands of times, not from an opinion. The dollar amounts are calibrated to a firm
like yours, not pulled from your ledger, so check them against your own numbers before you
quote them. Every figure in the report traces back to the record at the end of it.

This is a comparison engine, not a prediction of next year's P&L. It doesn't tell you what
*will* happen. It tells you which road ends up ahead, and why.
`.trim();

export default function HowItWorks({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 sm:p-8"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute right-3 top-3 rounded-md p-1.5 text-[var(--text-dim)] hover:bg-[var(--surface2)] hover:text-[var(--text)] cursor-pointer"
        >
          <X className="h-5 w-5" />
        </button>
        <div className="report-body px-6 py-6 sm:px-8 sm:py-8">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{HOW_IT_WORKS}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
