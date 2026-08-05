/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        base: '#0B0C10',
        surface: '#1F2833',
        surface2: '#2b3644',
        accent: '#45A29E', // Esmeralda discreto
        accentDark: '#36827F',
        muted: '#C5C6C7',
        text: '#ffffff',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        // Minimalista, quase 0
        DEFAULT: '2px',
        md: '2px',
        lg: '2px',
        xl: '4px',
      }
    },
  },
  plugins: [],
}
