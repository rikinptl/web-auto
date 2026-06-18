import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#07090f",
          900: "#0c1018",
          800: "#141b28",
          700: "#1e2838",
          600: "#2a3648",
          500: "#4a5a70",
          400: "#7a8da6",
          300: "#a8b8cc",
          200: "#d0dae6",
          100: "#eef2f7",
        },
        signal: {
          green: "#3dd68c",
          amber: "#f5b942",
          red: "#f07178",
          blue: "#59a6ff",
          violet: "#b48cff",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(255,255,255,0.06), 0 16px 48px rgba(0,0,0,0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
