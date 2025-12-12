import { ArtifactDetailClient } from "./ArtifactDetailClient"

// Disable dynamic params for static export
// All artifact IDs are handled client-side via the API
export const dynamicParams = false

// Static export: only generate placeholder routes
// Actual artifact data is fetched client-side
export function generateStaticParams(): Array<{ type: string; id: string }> {
  // Generate one placeholder route per artifact type
  // S3 will serve these pages, and client-side code handles the actual ID
  return [
    { type: "model", id: "placeholder" },
    { type: "dataset", id: "placeholder" },
    { type: "code", id: "placeholder" },
  ]
}

export default async function ArtifactDetailPage({ params }: { params: Promise<{ type: string; id: string }> }) {
  const { type, id } = await params

  // Validate type
  if (!['model', 'dataset', 'code'].includes(type)) {
    throw new Error(`Invalid artifact type: ${type}`)
  }

  return <ArtifactDetailClient type={type as 'model' | 'dataset' | 'code'} id={id} />
}

