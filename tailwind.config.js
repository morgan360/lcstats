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
        // Neutrals
        "mist": "#F0EFEB",

        // Accents
        "lime-glow": "#D8F878",
        "rose-pop": "#E47CB8",
        "violet-royal": "#9448B0",

        // Darks
        "indigo-deep": "#332277",
        "twilight": "#173251ff",
        "midnight": "#001C3D",
      },

      // Named gradients
      backgroundImage: {
        "gradient-01": "linear-gradient(180deg, #F0EFEB 0%, #D8F878 100%)",
        "gradient-02": "linear-gradient(180deg, #F0EFEB 0%, #E47CB8 100%)",
        "gradient-03": "linear-gradient(180deg, #E47CB8 0%, #9448B0 100%)",
        "gradient-04":
          "linear-gradient(180deg, #D8F878 0%, #E47CB8 45%, #9448B0 70%, #332277 100%)",
        "gradient-05": "linear-gradient(180deg, #9448B0 0%, #001C3D 100%)",
      },
    }
  },
  plugins: [],
}
