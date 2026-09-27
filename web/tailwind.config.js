/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Bus-factor scale; every use also carries a text label (WCAG).
        bf1: '#dc2626',
        bf2: '#d97706',
        bf3: '#16a34a',
        bfna: '#6b7280',
      },
    },
  },
  plugins: [],
};
