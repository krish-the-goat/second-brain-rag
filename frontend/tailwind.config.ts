import type { Config } from 'tailwindcss'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        brand: "#4f8ef7",
        surface: "#1a1d27",
        background: "#0f1117"
      }
    },
  },
  plugins: [],
} satisfies Config
