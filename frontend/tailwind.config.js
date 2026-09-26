/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        graphite: {
          950: '#0A0C0F',
          900: '#0E1116',
          850: '#141820',
          800: '#1B212D',
          700: '#2A3242',
          600: '#3D475C',
          500: '#5A667F',
        },
        ivory: {
          50: '#FAFAFA',
          100: '#F4F5F7',
          200: '#E9EBF0',
          300: '#DDE0E7',
        },
        coral: {
          50: '#FFF5F2',
          100: '#FFE6DF',
          200: '#FFCEBE',
          300: '#FFAA93',
          400: '#FF7D5D',
          500: '#FF5722',
          600: '#F03E0B',
          700: '#C72E04',
        },
        brand: {
          orange: '#FF5722',
          'orange-glow': 'rgba(255, 87, 34, 0.15)',
          'orange-subtle': '#FFF3EE',
          dark: '#0D1017',
          sidebar: '#0B0D13',
          surface: '#FFFFFF',
          canvas: '#F6F7F9',
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
        display: ['Outfit', 'Plus Jakarta Sans', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.03), 0 4px 12px rgba(0,0,0,0.02)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.06), 0 12px 24px rgba(0,0,0,0.03)',
        'float': '0 12px 32px -4px rgba(15, 23, 42, 0.08), 0 4px 12px -2px rgba(15, 23, 42, 0.03)',
        'glow-coral': '0 0 20px -3px rgba(255, 87, 34, 0.25)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      }
    },
  },
  plugins: [],
}
