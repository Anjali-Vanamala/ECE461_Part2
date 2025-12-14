/** @type {import('next').NextConfig} */
const nextConfig = {
  // Amplify supports Next.js SSR/SSG natively, so no static export needed
  // Dynamic routes and server-side rendering will work properly
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
