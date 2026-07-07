/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        geist: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        'geist-mono': ['var(--font-geist-mono)', 'monospace'],
      },
      colors: {
        // Primary teal palette (aligned with globals.css)
        primary: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',  // Main primary color
          600: '#0d9488',  // Main hover color
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
        // Brand color names for semantic usage
        brand: {
          primary: '#14b8a6',           // Teal - Main brand color
          'primary-hover': '#0d9488',   // Darker teal for hover
          'primary-light': '#99f6e4',   // Light teal
          secondary: '#4b5563',         // Medium gray
          background: '#f7f7f8',        // Light gray
          text: '#1d1d22',              // Dark text
          'text-secondary': '#4b5563',  // Medium gray text
          'text-muted': '#6b7280',      // Light gray text
          border: '#e5e5e9',            // Light border
        },
        // Semantic colors
        success: {
          DEFAULT: '#10b981',
          light: '#d1fae5',
        },
        warning: {
          DEFAULT: '#f59e0b',
          light: '#fef3c7',
        },
        error: {
          DEFAULT: '#ef4444',
          light: '#fee2e2',
        },
        info: {
          DEFAULT: '#3b82f6',
          light: '#dbeafe',
        },
        // Semantic colors for theme-aware components
        'card': 'var(--color-bg-card)',
        'hover': 'var(--color-bg-hover)',
        'primary': {
          DEFAULT: 'var(--color-text-primary)',
          foreground: 'var(--color-text-on-primary)',
        },
        'secondary': 'var(--color-text-secondary)',
        'muted': 'var(--color-text-muted)',
        'border': 'var(--color-border-default)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
