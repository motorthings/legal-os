# KPI Cards Documentation

## Overview

Two Bradbury Impact Loop-aligned KPI dashboard cards for displaying key performance metrics:

1. **CorrectionLoopCard** - Measures average turns to usable output
2. **IdeationVelocityCard** - Measures strategic drafts initiated per week

## Architecture

Both components follow identical patterns:
- Use `apiGet()` from `@/lib/api` for authenticated requests
- Implement proper error handling with retry mechanism
- Include accessibility features (ARIA labels, roles)
- Prevent memory leaks with mounted flag
- Use `useCallback` for optimal performance

## API Integration

### Important: No User ID Parameter

Both components fetch data for the **currently authenticated user** from the JWT token. They do NOT accept a `user_id` query parameter.

**Backend Endpoints:**
- `GET /api/kpis/correction-loop` - No query params
- `GET /api/kpis/ideation-velocity?time_period={period}` - Only accepts `time_period`

The backend uses `get_current_user()` dependency injection to identify the user from the Bearer token.

## Component Usage

### CorrectionLoopCard

```tsx
import CorrectionLoopCard from '@/components/CorrectionLoopCard';

// Simple usage - no props required
<CorrectionLoopCard />
```

**Data Returned:**
```typescript
{
  user_id: string;
  avg_turns_to_completion: number;
  total_completed_conversations: number;
  distribution: Record<string, number>;  // e.g., {'1_turn': 10, '2_turns': 25}
  goal_status: 'met' | 'close' | 'needs_improvement' | 'no_data';
}
```

**Goal Status:**
- `met`: avg < 2 turns (excellent)
- `close`: avg 2-3 turns (good)
- `needs_improvement`: avg > 3 turns
- `no_data`: No conversations yet

### IdeationVelocityCard

```tsx
import IdeationVelocityCard from '@/components/IdeationVelocityCard';

// Default: month view
<IdeationVelocityCard />

// Custom time period
<IdeationVelocityCard timePeriod="week" />
<IdeationVelocityCard timePeriod="month" />
<IdeationVelocityCard timePeriod="all_time" />
```

**Props:**
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `timePeriod` | `'week' \| 'month' \| 'all_time'` | `'month'` | Time range for data |

**Data Returned:**
```typescript
{
  user_id: string;
  time_period: string;
  drafts_initiated: number;
  avg_per_week: number;
  trend_data: Array<{ week: string; count: number }>;
}
```

## Example Dashboard Integration

```tsx
// app/admin/page.tsx or app/dashboard/page.tsx
import CorrectionLoopCard from '@/components/CorrectionLoopCard';
import IdeationVelocityCard from '@/components/IdeationVelocityCard';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <h1>Performance Metrics</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <CorrectionLoopCard />
        <IdeationVelocityCard timePeriod="month" />
      </div>
    </div>
  );
}
```

## Error Handling

Both components include:
- **Retry Mechanism**: Users can click "Try Again" on errors
- **Loading States**: Skeleton loaders while fetching
- **Error Messages**: Clear, user-friendly error text from `APIError`

## Accessibility

All components include:
- ARIA labels on all SVG icons
- `role="img"` and `role="progressbar"` attributes
- Descriptive aria-labels for screen readers
- Semantic HTML structure

## Authentication Required

Both components require:
1. Valid Supabase JWT token in request headers
2. User must have `client_id` in users table
3. Backend endpoints protected by `get_current_user()` dependency

If authentication fails, components will show error with retry button.

## Backend Dependencies

**Required Environment Variables:**
- `SUPABASE_JWT_SECRET` - For JWT validation
- `NEXT_PUBLIC_SUPABASE_URL` - Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase anon key

**Database Tables:**
- `users` (id, client_id, role)
- `conversations` (id, client_id, status)
- `messages` (id, conversation_id, role, content)

## Troubleshooting

**"User has no associated client" error:**
- User record missing `client_id` in database
- Add client_id to user: `UPDATE users SET client_id = ? WHERE id = ?`

**"Invalid authentication credentials" error:**
- JWT token expired or invalid
- User needs to re-authenticate

**No data showing:**
- Check if user has conversations in database
- Verify client_id matches between user and conversations
- Check backend logs for SQL/RPC errors

## Performance

Both components use:
- `useCallback` to prevent function recreations
- Mounted flag to prevent state updates after unmount
- Percentage clamping (0-100%) to prevent visual bugs
- Minimal re-renders with proper dependency arrays

## Future Enhancements

Potential improvements:
- Add time range selector for CorrectionLoopCard
- Export data to CSV/JSON
- Add comparison view (current vs previous period)
- Real-time updates with WebSocket
- Admin view to see all users' metrics
