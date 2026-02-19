/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Poppins', 'sans-serif'],
            },
            colors: {
                primary: '#0ea5e9', // Sky 500
                secondary: '#f0f9ff', // Sky 50
                glass: 'rgba(255, 255, 255, 0.7)',
            }
        },
    },
    plugins: [],
}
