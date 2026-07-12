'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HelpSource {
  title: string;
  heading: string;
  similarity: number;
  file_path: string;
}

export interface HelpMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: HelpSource[];
  feedback?: number | null;
  messageDbId?: string;
}

interface HelpChatContextType {
  isOpen: boolean;
  toggleOpen: () => void;
  messages: HelpMessage[];
  sendMessage: (text: string) => Promise<void>;
  clearMessages: () => void;
  isTyping: boolean;
  conversationId: string | null;
  submitFeedback: (messageId: string, feedback: number) => void;
  apiAvailable: boolean;
}

const HelpChatContext = createContext<HelpChatContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_LEGAL_OS_API_URL || 'http://localhost:8080';

// ---------------------------------------------------------------------------
// Fallback FAQ (used when API is unreachable)
// ---------------------------------------------------------------------------

interface FaqEntry {
  keywords: string[];
  answer: string;
}

const FALLBACK_FAQ: FaqEntry[] = [
  {
    keywords: ['what', 'legal', 'os', 'about', 'overview', 'platform'],
    answer:
      'Legal AI OS is a governed AI platform for legal enterprises. It provides an independent measurement, governance, and enablement layer around existing AI tools like Harvey AI. Key features include the Portfolio Dashboard for ROI tracking, POC Pipeline for project management, and Harvey Agent Monitoring for independent evaluation of AI outputs.',
  },
  {
    keywords: ['harvey', 'monitor', 'evaluate', 'score', 'accuracy', 'safety', 'bias', 'compliance'],
    answer:
      'Harvey Monitor provides independent 4-dimension evaluation of Harvey AI outputs: Accuracy, Safety, Bias, and Compliance. Scores are weighted (Tier 1 at 1.5x, Tier 2 at 1.0x) with a hard veto at 75. Certification: Platinum 90+, Gold 85+, Silver 80+, Bronze 75+. Register agents, run evaluations, and monitor drift from the Harvey Monitor page.',
  },
  {
    keywords: ['roi', 'cost', 'saved', 'dashboard', 'adoption', 'quality'],
    answer:
      'The ROI Framework measures AI performance across three dimensions: Cost Impact (time saved x billable rate), Quality Metrics (accuracy rate, override rate, false positive rate), and Adoption Rate (active users / eligible users). View everything on the Dashboard, which shows KPI cards, function breakdowns, and quality trends.',
  },
  {
    keywords: ['poc', 'pipeline', 'project', 'kanban', 'discovery', 'build', 'review'],
    answer:
      'The POC Pipeline tracks AI projects through five stages: Discovery → Build → Review → Graduated (or Cancelled). It provides a Kanban board view with project cards, status advance buttons, and a feedback log. Create new POCs, advance them through stages, and add feedback at any point.',
  },
  {
    keywords: ['drift', 'baseline', 'alert', 'degrad', 'monitor', 'detection'],
    answer:
      'Drift detection compares a Harvey agent\'s current output against its original baseline system prompt. Six drift types are monitored: Tone, Scope, Refusal, Instruction Erosion, Hallucination, and Safety. Drift scores range from 0 (no drift) to 100 (severe drift). Alerts fire automatically at 51+ with severity: moderate, high, or critical.',
  },
  {
    keywords: ['score', 'veto', 'certification', 'platinum', 'gold', 'silver', 'bronze'],
    answer:
      'The scoring engine uses a weighted formula: Accuracy/Safety/Bias at 1.5x weight, Compliance at 1.0x. A hard veto caps the final score at 74.9 if any Tier 1 dimension falls below 75. Certification levels: Platinum (90+), Gold (85-89), Silver (80-84), Bronze (75-79). Below 75 receives no certification.',
  },
  {
    keywords: ['governance', 'audit', 'rls', 'compliance', 'aba', 'confidential'],
    answer:
      'Legal AI OS governance is built on five pillars: Audit Trail (every LLM call recorded, append-only), Explainability (LLM provides reasoning, system provides judgment), Traceability (full lineage from input to output), Confidentiality (RLS-enforced client data isolation), and Human-in-the-Loop Gating (configurable review thresholds). ABA Formal Opinion 512 duties are addressed across all functions.',
  },
];

function findFallbackAnswer(question: string): string | null {
  const q = question.toLowerCase();
  let bestMatch: FaqEntry | null = null;
  let bestScore = 0;

  for (const entry of FALLBACK_FAQ) {
    const score = entry.keywords.filter(kw => q.includes(kw)).length;
    if (score > bestScore) {
      bestScore = score;
      bestMatch = entry;
    }
  }

  if (bestMatch && bestScore >= 2) {
    return bestMatch.answer;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function HelpChatProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<HelpMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [apiAvailable, setApiAvailable] = useState(true);

  const toggleOpen = useCallback(() => setIsOpen(o => !o), []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: HelpMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const response = await fetch(`${API_BASE}/api/help/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          question: text,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      const assistantMsg: HelpMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: data.answer,
        timestamp: new Date(),
        sources: data.sources,
        messageDbId: data.conversation_id,
      };

      setMessages(prev => [...prev, assistantMsg]);
      if (data.conversation_id) setConversationId(data.conversation_id);
      setApiAvailable(true);
    } catch {
      // Fallback: try local FAQ
      const fallbackAnswer = findFallbackAnswer(text);
      const assistantMsg: HelpMessage = {
        id: `assistant-fallback-${Date.now()}`,
        role: 'assistant',
        content: fallbackAnswer
          || "I couldn't connect to the help system right now. Try checking the guides at **Guides & Diagrams** in the sidebar, or ask again with a more specific question.",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      setApiAvailable(false);
    } finally {
      setIsTyping(false);
    }
  }, [conversationId]);

  const submitFeedback = useCallback(async (messageId: string, feedback: number) => {
    if (!messageId) return;
    try {
      await fetch(`${API_BASE}/api/help/feedback/${messageId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ feedback }),
      });
      setMessages(prev =>
        prev.map(m => (m.messageDbId === messageId ? { ...m, feedback } : m))
      );
    } catch {
      // Feedback is best-effort
    }
  }, []);

  return (
    <HelpChatContext.Provider
      value={{
        isOpen,
        toggleOpen,
        messages,
        sendMessage,
        clearMessages,
        isTyping,
        conversationId,
        submitFeedback,
        apiAvailable,
      }}
    >
      {children}
    </HelpChatContext.Provider>
  );
}

export function useHelpChat() {
  const ctx = useContext(HelpChatContext);
  if (!ctx) throw new Error('useHelpChat must be used within HelpChatProvider');
  return ctx;
}
