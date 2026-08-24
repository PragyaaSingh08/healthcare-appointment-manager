/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        forest: {
          50: '#eef4f2',
          100: '#d3e5e0',
          400: '#3d7a6b',
          600: '#245a4d',
          700: '#1a453b',
          900: '#0f2c26',
        },
        sage: {
          100: '#eef2ec',
          300: '#b9cbb4',
          500: '#6a8f7b',
        },
        amber: {
          100: '#fbecd9',
          400: '#d98e3f',
          600: '#b56a26',
        },
        clay: {
          500: '#c1543f',
        },
        ink: {
          900: '#1c2622',
          700: '#3a453f',
          400: '#75837b',
        },
        canvas: '#f5f6f2',
      },
      fontFamily: {
        display: ['"Fraunces"', 'serif'],
        body: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        card: '0.75rem',
      },
    },
  },
  plugins: [],
}
