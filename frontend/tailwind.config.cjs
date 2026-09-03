/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#f4f7fa",
        panel: "#ffffff",
        card: "#eef3f7",
        line: "#d9e2ec",
        muted: "#617287",
        cyan: "#087f8c",
        amber: "#a96710",
        danger: "#c43d4b",
      },
      boxShadow: {
        glow: "0 12px 32px rgba(15, 23, 42, 0.07)",
      },
    },
  },
  plugins: [],
};
