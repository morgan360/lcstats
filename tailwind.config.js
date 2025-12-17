/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/*.html',
    './**/*.js',
    './**/*.py',
    './static/src/**/*.css'
  ],
  theme: {
    extend: {
      colors: {
        'off-white': '#F7F9FC',
        'off-black': '#0F1214',

        'cinza-escuro': '#25282A',
        'cinza-sereno': '#DDE5ED',
        'verde-menta': '#A7E6D7',
        'lavanda': '#685BC7',
        'azul-naval': '#001871',
      }
    }
  },
  plugins: [],
}
