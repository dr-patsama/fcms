/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './app/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Cloud', 'sans-serif'],
        cloud: ['Cloud', 'sans-serif'],
      },
      colors: {
        // Ruby Red
        ruby: {
          DEFAULT: '#E0115F',
          light:   '#FF4D8D',
          dark:    '#A00040',
          muted:   '#FCE4EE',
        },
        // Emerald Green
        emerald: {
          DEFAULT: '#009473',
          vivid:   '#50C878',
          dark:    '#006B54',
          muted:   '#E0F5EF',
        },
        // Sapphire Blue
        sapphire: {
          DEFAULT: '#0F52BA',
          deep:    '#151667',
          light:   '#4A7FD4',
          muted:   '#E8EEFA',
        },
      },
      borderRadius: {
        sm:  '6px',
        DEFAULT: '10px',
        lg:  '16px',
        xl:  '24px',
        '2xl': '32px',
      },
      boxShadow: {
        sm:   '0 1px 3px rgba(0,0,0,0.08)',
        DEFAULT: '0 4px 12px rgba(0,0,0,0.10)',
        lg:   '0 8px 24px rgba(0,0,0,0.12)',
        card: '0 2px 8px rgba(15,82,186,0.08)',
      },
      fontSize: {
        xs:   '11px',
        sm:   '13px',
        base: '15px',
        lg:   '17px',
        xl:   '20px',
        '2xl':'24px',
        '3xl':'30px',
        '4xl':'36px',
      },
    },
  },
  plugins: [],
}
