/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          900: "#0F172A",
          700: "#1E293B",
          500: "#334155",
          100: "#E2E8F0"
        }
      }
    }
  },
  plugins: []
};
