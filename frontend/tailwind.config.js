/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f1115",
        panel: "#171a21",
        panel2: "#1f232c",
        brand: "#7c5cff",
        brand2: "#5b8cff",
        good: "#34d399",
        warn: "#fbbf24",
        bad: "#f87171",
        muted: "#8b93a7",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
