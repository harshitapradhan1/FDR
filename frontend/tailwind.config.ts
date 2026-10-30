import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        aicte: {
          navy: "#1B365D",
          darkNavy: "#0F2137",
          saffron: "#FF9933",
          saffronDark: "#E67E22",
          emerald: "#138808",
          emeraldDark: "#0E6606",
          gold: "#D4AF37",
        }
      },
    },
  },
  plugins: [],
};
export default config;
