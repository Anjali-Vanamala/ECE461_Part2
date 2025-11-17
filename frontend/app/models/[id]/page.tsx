import { ModelDetailClient } from "./ModelDetailClient"

// Required for static export with dynamic routes
// This server component exports generateStaticParams() to satisfy static export requirements
// The actual UI is in ModelDetailClient.tsx (client component)
export function generateStaticParams() {
  // These IDs match the mock data currently used throughout the frontend
  // See: frontend/app/browse/page.tsx and frontend/components/model-grid.tsx
  // TODO: When integrating with real API, fetch model IDs from API at build time
  return [
    { id: "bert-base" },
    { id: "resnet-50" },
    { id: "gpt2-small" },
  ]
}

export default function ModelDetailPage({ params }: { params: { id: string } }) {
  return <ModelDetailClient id={params.id} />
}
