/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',  // Enable static export for S3 deployment
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
