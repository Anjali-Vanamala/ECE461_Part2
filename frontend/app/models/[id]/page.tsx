import { ModelDetailClient } from "./ModelDetailClient"

// Required for static export with dynamic routes
// This server component exports generateStaticParams() to satisfy static export requirements
// The actual UI is in ModelDetailClient.tsx (client component)
export function generateStaticParams() {
  // For static export, we need to pre-generate pages for known model IDs
  // Since we can't fetch from API at build time easily, return empty array
  // This means no static pages will be pre-generated, but the route will work
  // TODO: If you want to pre-generate pages, fetch model IDs from API at build time here
  return []
}

export default function ModelDetailPage({ params }: { params: { id: string } }) {
  // For static export, params are always synchronous
  return <ModelDetailClient id={params.id} />
}
