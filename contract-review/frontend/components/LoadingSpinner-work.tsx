/**
 * LoadingSpinner Component
 *
 * Standardized loading spinner for the application.
 * Uses CSS classes from globals.css for consistent styling.
 *
 * Usage:
 *   <LoadingSpinner size="sm" />
 *   <LoadingSpinner size="md" />
 *   <LoadingSpinner size="lg" />
 *   <LoadingSpinner type="dots" />
 */

import { memo } from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  type?: 'spinner' | 'dots'
  className?: string
}

function LoadingSpinner({
  size = 'md',
  type = 'spinner',
  className = ''
}: LoadingSpinnerProps) {

  if (type === 'dots') {
    return (
      <div className={`spinner-dots ${className}`}>
        <div className="spinner-dot" style={{ animationDelay: '0ms' }}></div>
        <div className="spinner-dot" style={{ animationDelay: '150ms' }}></div>
        <div className="spinner-dot" style={{ animationDelay: '300ms' }}></div>
      </div>
    )
  }

  return (
    <div className={`spinner spinner-${size} ${className}`} role="status" aria-label="Loading">
      <span className="sr-only">Loading...</span>
    </div>
  )
}

export default memo(LoadingSpinner);
