/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"DM Serif Display"', 'Georgia', 'serif'],
        mono: ['"DM Mono"', 'monospace'],
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      colors: {
        bg: '#0a0a0b',
        surface: '#111114',
        border: '#1e1e28',
        muted: '#2a2a35',
        text: '#f0ede8',
        subtle: '#8b8899',
        dim: '#4a4858',
        accent: '#e8a855',
      },
    },
  },
  plugins: [],
}
