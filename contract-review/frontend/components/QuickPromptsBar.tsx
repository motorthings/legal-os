'use client';

import { useState, useEffect } from 'react';
import { apiGet, apiPost } from '@/lib/api';
import { logger } from '@/lib/logger';

interface QuickPrompt {
  id: string;
  prompt_text: string;
  function_name?: string;
  usage_count: number;
  active: boolean;
  display_order?: number;
}

interface QuickPromptsBarProps {
  onPromptClick: (promptText: string) => void;
}

export default function QuickPromptsBar({ onPromptClick }: QuickPromptsBarProps) {
  const [prompts, setPrompts] = useState<QuickPrompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    fetchQuickPrompts();
  }, []);

  const fetchQuickPrompts = async () => {
    try {
      const response = await apiGet<{ success: boolean; prompts: QuickPrompt[] }>('/api/quick-prompts?active_only=true');
      if (response.success) {
        setPrompts(response.prompts || []);
      }
    } catch (error) {
      logger.error('Error fetching quick prompts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = async (prompt: QuickPrompt) => {
    // Track usage
    try {
      await apiPost(`/api/quick-prompts/${prompt.id}/use`, {});
    } catch (error) {
      logger.error('Error tracking prompt usage:', error);
    }

    // Send message
    onPromptClick(prompt.prompt_text);
  };

  if (loading) {
    return (
      <div className="quick-prompts-bar py-2">
        <div className="text-xs text-muted">Loading quick prompts...</div>
      </div>
    );
  }

  if (prompts.length === 0) {
    return null; // Don't show if no prompts
  }

  // Show first 5 prompts by default, or all if showAll is true
  const displayedPrompts = showAll ? prompts : prompts.slice(0, 5);

  return (
    <div className="quick-prompts-bar mb-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-medium text-secondary uppercase tracking-wide">
          Quick Prompts
        </h3>
        {prompts.length > 5 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-xs text-primary hover:underline"
          >
            {showAll ? 'Show Less' : `Show All (${prompts.length})`}
          </button>
        )}
      </div>

      <div className="prompt-chips-container flex flex-wrap gap-2">
        {displayedPrompts.map((prompt) => (
          <button
            key={prompt.id}
            className="prompt-chip px-3 py-1.5 rounded-full bg-primary-50 hover:bg-primary-100 text-primary text-sm transition-all hover:shadow-sm border border-primary-200 hover:border-primary-300"
            onClick={() => handlePromptClick(prompt)}
            title={prompt.function_name ? `Function: ${prompt.function_name}` : 'Quick prompt'}
          >
            {prompt.prompt_text}
          </button>
        ))}
      </div>
    </div>
  );
}
