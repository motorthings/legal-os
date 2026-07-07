# SuperAssistant Frontend Color System

## Overview

This document defines the standardized color system for the SuperAssistant frontend application. All colors are WCAG AA compliant and organized for consistency and maintainability.

---

## Design Principles

1. **Consistency**: Use CSS classes, not inline styles or one-off color utilities
2. **Accessibility**: All color combinations meet WCAG AA standards (minimum 4.5:1 contrast)
3. **Maintainability**: Colors defined once in `globals.css`, referenced everywhere
4. **Semantic Naming**: Class names describe purpose, not appearance
5. **No Dark Mode**: Simplified to single light theme for consistency

---

## Color Palette

### Primary Brand Color
- **Teal (#14b8a6)** - Main brand color, used for primary actions and emphasis
- **Hover: #0d9488** - Darker teal for hover states

### Text Colors (WCAG AA Compliant)
- **Primary Text: #1d1d22** - Main text, headings (16.5:1 contrast on white)
- **Secondary Text: #4b5563** - Less prominent text (7.4:1 contrast on white)
- **Muted Text: #6b7280** - Tertiary/helper text (4.6:1 contrast on white)
- **On Primary: #ffffff** - Text on teal backgrounds

### Background Colors
- **Page: #f7f7f8** - Light gray page backgrounds
- **Card: #ffffff** - White cards and containers
- **Hover: #f7f7f8** - Hover state backgrounds
- **Disabled: #f3f4f6** - Disabled element backgrounds
- **Input: #f7f7f8** - Form input backgrounds

### Border Colors
- **Default: #e5e5e9** - Standard borders
- **Hover: #d1d5db** - Border hover states
- **Focus: #14b8a6** - Focus ring indicators
- **Disabled: #e5e7eb** - Disabled element borders

### Semantic Colors
- **Success: #10b981** (green) - Success states, checkmarks
- **Warning: #f59e0b** (amber) - Warning states, alerts
- **Error: #ef4444** (red) - Error states, validation
- **Info: #3b82f6** (blue) - Informational states

---

## CSS Class Reference

### Button Classes

#### `.btn-primary`
Primary call-to-action button
```tsx
<button className="btn-primary">Save Changes</button>
```
- Background: Teal (#14b8a6)
- Text: White
- Hover: Darker teal with opacity
- Disabled: Light gray

#### `.btn-secondary`
Secondary action button
```tsx
<button className="btn-secondary">Cancel</button>
```
- Background: White
- Border: Light gray
- Text: Dark
- Hover: Light gray background

#### `.btn-icon`
Icon-only button (e.g., attachment button)
```tsx
<button className="btn-icon">📎</button>
```
- Background: White
- Border: Light gray
- Padding optimized for icons

---

### Text Classes

#### `.text-primary`
Primary text color for headings and important content
```tsx
<h1 className="text-primary">Welcome</h1>
<p className="text-primary">Important message</p>
```

#### `.text-secondary`
Secondary text for less prominent content
```tsx
<p className="text-secondary">Additional details</p>
```

#### `.text-muted`
Muted text for helper text, timestamps, labels
```tsx
<span className="text-muted">2 hours ago</span>
<p className="text-muted">Optional field</p>
```

#### `.text-brand`
Brand-colored text (teal) for logos and emphasis
```tsx
<h1 className="text-brand">SuperAssistant</h1>
```

#### `.icon-primary`
Primary color for icons
```tsx
<svg className="icon-primary">...</svg>
```

#### `.icon-muted`
Muted color for secondary icons
```tsx
<svg className="icon-muted">...</svg>
```

---

### Form Classes

#### `.input-field`
Standard text input
```tsx
<input type="text" className="input-field" />
```
- Full width, padding, rounded corners
- Light gray background
- Focus ring in teal
- Disabled state styling

#### `.textarea-field`
Multi-line textarea
```tsx
<textarea className="textarea-field" rows={4} />
```
- Similar to input-field but optimized for multi-line
- Non-resizable by default

#### `.label`
Form label
```tsx
<label className="label">Email Address</label>
```
- Small, medium weight
- Primary text color

#### `.form-helper`
Helper/hint text below inputs
```tsx
<p className="form-helper">Enter your email address</p>
```
- Extra small text
- Muted color

#### `.form-error`
Error message text
```tsx
<p className="form-error">Email is required</p>
```
- Small text
- Error red color

---

### Container Classes

#### `.card`
Basic card container
```tsx
<div className="card">
  <p>Card content</p>
</div>
```
- White background
- Light border
- Rounded corners
- Subtle shadow

#### `.card-interactive`
Clickable/hoverable card
```tsx
<div className="card-interactive">
  <p>Click me</p>
</div>
```
- Same as `.card` but with hover effects
- Pointer cursor
- Enhanced shadow on hover

#### `.page-bg`
Page-level background
```tsx
<div className="page-bg min-h-screen">
  {/* page content */}
</div>
```
- Light gray background (#f7f7f8)

---

### Badge Classes

#### `.badge-primary`
Primary badge (teal background)
```tsx
<span className="badge-primary">Active</span>
```

#### `.badge-secondary`
Secondary badge (gray background)
```tsx
<span className="badge-secondary">Pending</span>
```

#### `.badge-success`
Success badge (green background)
```tsx
<span className="badge-success">✓ Processed</span>
```

#### `.badge-warning`
Warning badge (amber background)
```tsx
<span className="badge-warning">⚠ Warning</span>
```

#### `.badge-error`
Error badge (red background)
```tsx
<span className="badge-error">✗ Failed</span>
```

---

### Avatar Classes

#### `.avatar-primary`
Primary avatar circle (teal background)
```tsx
<div className="avatar-primary w-12 h-12">
  {user.name.charAt(0).toUpperCase()}
</div>
```
- Teal background
- White text
- Flexbox centered
- Must add explicit size (w-* h-*)

#### `.avatar-secondary`
Secondary avatar (gray background)
```tsx
<div className="avatar-secondary w-10 h-10">JD</div>
```

---

### Chat Message Classes

#### `.message-user`
User's chat message bubble
```tsx
<div className="message-user">
  <p>Hello!</p>
</div>
```
- Teal background
- White text
- Rounded corners
- Max width 70%

#### `.message-assistant`
Assistant's chat message bubble
```tsx
<div className="message-assistant">
  <p>How can I help you?</p>
</div>
```
- Light gray background
- Dark text
- Rounded corners
- Max width 70%

#### `.message-timestamp`
Timestamp in message bubbles
```tsx
<div className="message-timestamp">2:45 PM</div>
```
- Extra small text
- 70% opacity

---

### Sidebar/Navigation Classes

#### `.sidebar-item`
Clickable sidebar item
```tsx
<button className="sidebar-item">
  <svg className="icon-muted" />
  <span>Home</span>
</button>
```
- Padding and rounded corners
- Hover background
- Smooth transitions

#### `.sidebar-item-active`
Active/selected sidebar item
```tsx
<button className="sidebar-item-active">
  <span>Current Page</span>
</button>
```
- Light background
- Teal text color
- Medium font weight

---

### Progress & Loading Classes

#### `.progress-bar-container`
Container for progress bars
```tsx
<div className="progress-bar-container">
  <div className="progress-bar-fill" style={{ width: '60%' }} />
</div>
```

#### `.progress-bar-fill`
Progress bar fill (teal)
- Set width dynamically with inline style

#### `<LoadingSpinner />`
Standardized loading spinner component
```tsx
import LoadingSpinner from '@/components/LoadingSpinner'

<LoadingSpinner size="sm" />
<LoadingSpinner size="md" />
<LoadingSpinner size="lg" />
<LoadingSpinner type="dots" /> // For chat loading
```
- **Use this instead of inline spinners!**
- Consistent teal color
- Three sizes available
- Dots variant for chat loading

---

### Stats & Metrics Classes

#### `.stat-number`
Large stat number (teal, bold)
```tsx
<div className="stat-number">1,247</div>
```

#### `.stat-label`
Stat description label
```tsx
<div className="stat-label">Total Users</div>
```

---

### Utility Classes

#### `.border-default`
```tsx
<div className="border border-default">...</div>
```

#### `.bg-card`
```tsx
<div className="bg-card">...</div>
```

#### `.bg-page`
```tsx
<div className="bg-page">...</div>
```

#### `.bg-hover`
```tsx
<div className="bg-hover">...</div>
```

#### `.link`
Styled hyperlink
```tsx
<a href="/forgot-password" className="link">
  Forgot password?
</a>
```

#### `.divider`
Horizontal divider line
```tsx
<div className="divider" />
```

---

## Migration Guide

### Replacing Inline Colors

| **Old (Inline Style)** | **New (CSS Class)** |
|------------------------|---------------------|
| `style={{ backgroundColor: '#14b8a6' }}` (button) | `className="btn-primary"` |
| `style={{ color: '#1d1d22' }}` | `className="text-primary"` |
| `style={{ color: '#6c6c89' }}` | `className="text-muted"` |
| `style={{ backgroundColor: '#f7f7f8' }}` | `className="bg-page"` or `"bg-hover"` |
| `style={{ borderColor: '#e5e5e9' }}` | `className="border-default"` |

### Replacing Tailwind Color Utilities

| **Old (Tailwind)** | **New (CSS Class)** |
|--------------------|---------------------|
| `bg-blue-600` (button) | `.btn-primary` |
| `text-blue-600` (icon) | `.icon-primary` |
| `text-blue-600 text-3xl font-bold` (stat) | `.stat-number` |
| `text-gray-600` | `.text-secondary` |
| `text-gray-500` or `text-gray-400` | `.text-muted` |
| `bg-white` | `.bg-card` or `.card` |
| `bg-gray-50` or `bg-gray-100` | `.bg-page` or `.bg-hover` |
| `border-gray-200` | `.border-default` |

### Replacing Inline Spinners

**Old:**
```tsx
<div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
```

**New:**
```tsx
import LoadingSpinner from '@/components/LoadingSpinner'

<LoadingSpinner size="sm" />
```

---

## Best Practices

### ✅ DO:
- Use CSS classes from `globals.css` for all styling
- Use `<LoadingSpinner />` component for loading states
- Apply semantic classes (`.btn-primary`, `.text-muted`, etc.)
- Test color contrast with browser dev tools
- Use `.card` or `.card-interactive` for container styling
- Import and use `LoadingSpinner` component

### ❌ DON'T:
- Don't use inline `style={{}}` for colors
- Don't use one-off Tailwind color utilities (bg-blue-600, text-gray-500, etc.)
- Don't hardcode hex colors in components
- Don't create custom inline spinners
- Don't use `!important` to override color classes
- Don't mix inline styles with CSS classes

---

## Accessibility Checklist

When using the color system, verify:

- [ ] Text meets minimum 4.5:1 contrast ratio on its background
- [ ] Focus indicators are visible (teal ring, 3px)
- [ ] Interactive elements have hover/active states
- [ ] Color is not the only means of conveying information (use icons + text)
- [ ] Disabled states are clearly distinguishable
- [ ] Links are underlined or otherwise distinguishable from body text

---

## Examples

### Login Form
```tsx
<div className="min-h-screen bg-page flex items-center justify-center">
  <div className="card max-w-md w-full p-8">
    <h1 className="heading-2 mb-6">Sign In</h1>

    <div className="mb-4">
      <label className="label">Email</label>
      <input type="email" className="input-field" />
    </div>

    <div className="mb-6">
      <label className="label">Password</label>
      <input type="password" className="input-field" />
      <p className="form-helper">Must be at least 8 characters</p>
    </div>

    <button className="btn-primary w-full">Sign In</button>

    <p className="text-muted text-center mt-4">
      <a href="/forgot-password" className="link">Forgot password?</a>
    </p>
  </div>
</div>
```

### Admin Dashboard Card
```tsx
<div className="card-interactive p-6">
  <div className="flex items-center justify-between mb-4">
    <h3 className="heading-3">Total Users</h3>
    <svg className="icon-primary w-6 h-6">...</svg>
  </div>
  <div className="stat-number">1,247</div>
  <p className="stat-label">Active this month</p>
</div>
```

### Chat Interface
```tsx
<div className="page-bg h-screen">
  {loading ? (
    <div className="flex justify-center py-8">
      <LoadingSpinner size="md" />
    </div>
  ) : (
    <div className="message-user">
      Hello, how are you?
      <div className="message-timestamp">2:45 PM</div>
    </div>
  )}
</div>
```

---

## File Locations

- **Color System Definition**: `/frontend/app/globals.css`
- **Tailwind Config**: `/frontend/tailwind.config.js`
- **LoadingSpinner Component**: `/frontend/components/LoadingSpinner.tsx`
- **This Documentation**: `/frontend/COLOR_SYSTEM.md`

---

## Questions or Issues?

If you encounter:
- **Missing color class**: Check if it should be added to `globals.css`
- **Contrast issues**: Use browser dev tools to verify WCAG compliance
- **Inconsistent appearance**: Ensure you're not mixing inline styles with CSS classes
- **Undefined Tailwind classes**: Check that `tailwind.config.js` has the color defined

For new color needs, consider:
1. Can an existing class be reused?
2. Is this a one-off need, or will it be used multiple places?
3. Does it fit the semantic naming convention?

Add new classes to `globals.css` only if they'll be reused across multiple components.

---

**Last Updated**: November 2025
**Version**: 1.0
