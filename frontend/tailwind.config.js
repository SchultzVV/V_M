/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    // Override Tailwind's default border-radius — DEF is brutalist, no rounded corners
    borderRadius: {
      'none': '0',
      DEFAULT: '0',
      'sm': '0',
      'md': '0',
      'lg': '0',
      'xl': '0',
      '2xl': '0',
      'full': '9999px', // kept for avatars/pills only when explicitly needed
    },
    extend: {
      colors: {
        // DEF Brand - Neon accents
        'neon-green': '#00ff41',
        'neon-red': '#ff004d',
        'neon-green-dim': '#00cc33',
        'neon-red-dim': '#cc003d',

        // DEF Brand - Dark palette
        'dark-gray': '#1a1a1a',      // Card background
        'black-deep': '#0a0a0a',     // Page background
        'gray-steel': '#2a2a2a',     // Secondary surfaces / inputs
        'gray-light': '#d1d5db',     // Highlighted text / labels
        'gray-text': '#9ca3af',      // Secondary / meta text
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['IBM Plex Mono', 'monospace'],
      },
      fontSize: {
        'price': ['3rem', { lineHeight: '1' }],      // 48px — hero prices
        'price-sm': ['1.5rem', { lineHeight: '1' }], // 24px — card prices
      },
      spacing: {
        'gutter': '1.5rem',
      },
      aspectRatio: {
        'square': '1 / 1',
        'video': '16 / 9',
      },
      // Neon glow box-shadows for hover/active states
      boxShadow: {
        'neon-red': '0 0 8px #ff004d, 0 0 24px rgba(255,0,77,0.3)',
        'neon-green': '0 0 8px #00ff41, 0 0 24px rgba(0,255,65,0.3)',
      },
    },
  },
  plugins: [],
}
