/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // DEF Brand - Neon colors
        'neon-green': '#00ff41',
        'neon-red': '#ff004d',
        'neon-green-dim': '#00cc33',
        'neon-red-dim': '#cc003d',
        
        // DEF Brand - Dark palette
        'dark-gray': '#1a1a1a',      // Card background
        'black-deep': '#0a0a0a',     // Page background
        'gray-steel': '#2a2a2a',     // Secondary surfaces
        'gray-light': '#d1d5db',     // Text light
        'gray-text': '#9ca3af',      // Secondary text
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['IBM Plex Mono', 'monospace'],
      },
      fontSize: {
        'price': ['3rem', { lineHeight: '1' }],      // 48px for prices
        'price-sm': ['1.5rem', { lineHeight: '1' }], // 24px for small prices
      },
      spacing: {
        'gutter': '1.5rem',
      },
      aspectRatio: {
        'square': '1 / 1',
        'video': '16 / 9',
      },
    },
  },
  plugins: [],
}
