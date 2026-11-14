const token = (name) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: token('canvas'),
        panel: token('panel'),
        sunken: token('sunken'),
        line: token('line'),
        'line-strong': token('line-strong'),
        fg: token('fg'),
        muted: token('muted'),
        faint: token('faint'),
        report: token('report'),
        both: token('both'),
        web: token('web'),
        danger: token('danger'),
      },
      fontFamily: {
        sans: ['"Overpass Variable"', 'system-ui', 'sans-serif'],
      },
      borderRadius: { panel: '16px', control: '10px' },
      transitionTimingFunction: { out: 'cubic-bezier(.2,.9,.3,1)' },
      keyframes: {
        shimmer: { '0%': { backgroundPosition: '200% 0' }, '100%': { backgroundPosition: '-200% 0' } },
        blink: { '50%': { opacity: '0' } },
      },
      animation: { shimmer: 'shimmer 1.6s linear infinite', blink: 'blink 1s steps(1) infinite' },
    },
  },
  plugins: [],
}
