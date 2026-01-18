/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        urgent: {
          light: '#fef2f2',
          DEFAULT: '#ef4444',
          dark: '#991b1b',
        },
        routine: {
          light: '#fffbeb',
          DEFAULT: '#f59e0b',
          dark: '#92400e',
        },
        normal: {
          light: '#f0fdf4',
          DEFAULT: '#22c55e',
          dark: '#166534',
        },
      },
    },
  },
  plugins: [],
};
