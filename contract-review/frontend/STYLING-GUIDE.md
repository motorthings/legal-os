# SuperAssistant Styling Guide

This guide shows how to use the reusable CSS classes defined in `app/globals.css` for consistent dark mode theming.

## Quick Reference

### Input Fields
```tsx
// Before (long and repetitive):
<input
  className="w-full px-4 py-2 border-2 border-[#e5e5e9] dark:border-gray-500 rounded-lg bg-white dark:bg-gray-600 text-[#1d1d22] dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-[#f7f7f8] dark:disabled:bg-gray-700 disabled:cursor-not-allowed"
/>

// After (clean and simple):
<input className="input-field" />
```

### Buttons
```tsx
// Primary Button
<button className="btn-primary">
  Sign In
</button>

// Secondary Button
<button className="btn-secondary">
  Cancel
</button>
```

### Page Layout
```tsx
// Page with background
<div className="page-bg min-h-screen p-8">
  {/* Card container */}
  <div className="card p-6">
    <h1 className="heading-1 mb-4">Welcome</h1>
    <p className="text-secondary">Some descriptive text</p>
  </div>
</div>
```

### Typography
```tsx
// Headings
<h1 className="heading-1">Main Title</h1>
<h2 className="heading-2">Section Title</h2>
<h3 className="heading-3">Subsection</h3>

// Text Colors
<p className="text-primary">Primary text (high contrast)</p>
<p className="text-secondary">Secondary text (medium contrast)</p>
<p className="text-muted">Muted text (low contrast)</p>

// Labels
<label className="label">Email Address</label>

// Links
<a href="/profile" className="link">View Profile</a>
```

### Other Components
```tsx
// Cards/Containers
<div className="card p-6">
  Card content here
</div>

// Dividers
<div className="divider my-4"></div>
```

## Complete Example

Here's a full form example using the new classes:

```tsx
export default function ExampleForm() {
  return (
    <div className="page-bg min-h-screen flex items-center justify-center p-8">
      <div className="max-w-md w-full">
        <h1 className="heading-1 mb-2">Create Account</h1>
        <p className="text-secondary mb-8">Fill in your details to get started</p>

        <div className="card p-8">
          <form>
            {/* Name Field */}
            <div className="mb-4">
              <label htmlFor="name" className="label">
                Full Name
              </label>
              <input
                id="name"
                type="text"
                className="input-field"
                placeholder="John Doe"
              />
            </div>

            {/* Email Field */}
            <div className="mb-4">
              <label htmlFor="email" className="label">
                Email
              </label>
              <input
                id="email"
                type="email"
                className="input-field"
                placeholder="you@example.com"
              />
            </div>

            <div className="divider my-6"></div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button type="submit" className="btn-primary flex-1">
                Create Account
              </button>
              <button type="button" className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>

          <div className="mt-6 text-center">
            <p className="text-muted">
              Already have an account?{' '}
              <a href="/auth/login" className="link">Sign in</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

## Available Classes

| Class | Purpose | Dark Mode Support | WCAG Compliance |
|-------|---------|-------------------|-----------------|
| `.input-field` | Text inputs, textareas | ✅ Yes | AA |
| `.btn-primary` | Primary action buttons | ✅ Yes | AA |
| `.btn-secondary` | Secondary buttons | ✅ Yes | AA |
| `.card` | Containers/cards | ✅ Yes | AA |
| `.page-bg` | Page backgrounds | ✅ Yes | AA |
| `.text-primary` | High contrast text | ✅ Yes | AA (4.5:1) |
| `.text-secondary` | Medium contrast text | ✅ Yes | AA (4.5:1) |
| `.text-muted` | Low contrast text | ✅ Yes | AA |
| `.text-accent` | Accent/primary color text | ✅ Yes | AA (8:1) |
| `.bg-accent` | Accent/primary backgrounds | ✅ Yes | AA |
| `.icon-color` | SVG icons | ✅ Yes | AA (8:1) |
| `.stat-number` | Large stats/numbers | ✅ Yes | AAA (8:1) |
| `.heading-1` | H1 headings | ✅ Yes | AA |
| `.heading-2` | H2 headings | ✅ Yes | AA |
| `.heading-3` | H3 headings | ✅ Yes | AA |
| `.link` | Links with hover | ✅ Yes | AA |
| `.label` | Form labels | ✅ Yes | AA |
| `.divider` | Horizontal dividers | ✅ Yes | AA |

## WCAG Accessibility Standards

All color classes follow WCAG AA accessibility guidelines:

- **Normal text**: 4.5:1 minimum contrast ratio
- **Large text** (18pt+): 3:1 minimum contrast ratio
- **Icons and stats**: 8:1+ contrast ratio (AAA level)

### Using Accent Colors for Consistency

```tsx
// Icons - Use .icon-color class
<svg className="w-6 h-6 icon-color" fill="none" stroke="currentColor">
  {/* ... */}
</svg>

// Stats/Numbers - Use .stat-number class
<div className="stat-number">{totalClients}</div>
<div className="text-sm text-secondary mt-1">Total Clients</div>

// Accent text - Use .text-accent class
<span className="text-accent">Important information</span>

// Accent backgrounds - Use .bg-accent class
<button className="bg-accent text-white px-4 py-2 rounded">Action</button>
```

## Benefits

✅ **WCAG AA Compliant** - Meets accessibility standards for contrast
✅ **Consistent styling** - All dark mode colors are centralized
✅ **Shorter code** - No more repeating long className strings
✅ **Easy maintenance** - Update styles in one place
✅ **Type-safe** - Still works with Tailwind IntelliSense
✅ **Flexible** - Can still add additional Tailwind classes as needed

## Extending Classes

You can still add additional Tailwind utilities alongside these classes:

```tsx
<input className="input-field max-w-xs" />
<button className="btn-primary w-full">Full Width Button</button>
<div className="card p-6 max-w-2xl mx-auto">Custom card</div>
```

## Need More Classes?

To add new component classes, edit `app/globals.css` and add your class using the same pattern:

```css
.your-class-name {
  @apply /* your Tailwind utilities */;
  @apply /* dark mode variants */;
}
```
