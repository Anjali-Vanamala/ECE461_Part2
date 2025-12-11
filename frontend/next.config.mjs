/** @type {import('next').NextConfig} */
const nextConfig = {
  // Only use static export in production builds (for S3 deployment)
  // In development, allow dynamic routes to work properly
  ...(process.env.NODE_ENV === 'production' ? { output: 'export' } : {}),
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
