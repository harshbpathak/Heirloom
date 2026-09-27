/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      colors: {
        // Neo-brutalist palette (CSS variables so dark mode can swap ink/paper).
        ink: 'var(--ink)',
        'ink-soft': 'var(--ink-soft)',
        paper: 'var(--paper)',
        'paper-light': 'var(--paper-light)',
        night: 'var(--night)',
        sun: 'var(--sun)',
        coral: 'var(--coral)',
        mint: 'var(--mint)',
        violet: 'var(--violet)',
        danger: 'var(--danger)',
        // Brand palette (kept for existing pages; mapped onto violet).
        brand: {
          50: '#f1edff',
          100: '#e3dcff',
          500: '#7b5cff',
          600: '#6a4be6',
          700: '#573bc7',
        },
        // Bus-factor scale; every use also carries a text label (WCAG).
        bf1: '#c92a2a', // red-8 (darker for AA contrast on white)
        bf2: '#e67700', // orange-8
        bf3: '#2f9e44', // green-8
        bfna: '#868e96', // gray-6
      },
      boxShadow: {
        brutal: '4px 4px 0 var(--ink)',
        'brutal-sm': '3px 3px 0 var(--ink)',
        'brutal-lg': '8px 8px 0 var(--ink)',
        'brutal-xl': '10px 10px 0 var(--ink)',
        'brutal-coral': '10px 10px 0 var(--coral)',
      },
    },
  },
  plugins: [],
};
