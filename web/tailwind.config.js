/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        academic: {
          blue: '#1e3a8a',
          indigo: '#312e81',
          slate: '#0f172a',
          subtle: '#f8fafc',
          card: '#ffffff',
          border: '#e2e8f0',
          accent: '#0284c7',
        },
        optimal: {
          DEFAULT: '#059669',
          bg: '#ecfdf5',
          border: '#a7f3d0',
          text: '#065f46',
        },
        inverted: {
          DEFAULT: '#dc2626',
          bg: '#fef2f2',
          border: '#fecaca',
          text: '#991b1b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['Merriweather', 'Georgia', 'serif'],
        mono: ['Fira Code', 'Consolas', 'Monaco', 'monospace'],
      },
    },
  },
  plugins: [],
}
