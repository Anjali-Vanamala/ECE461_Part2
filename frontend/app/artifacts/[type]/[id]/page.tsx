import { ArtifactDetailClient } from "./ArtifactDetailClient"

// Allow dynamic params for this route
export const dynamicParams = true

// For static export builds, generate placeholder params
export function generateStaticParams(): Array<{ type: string; id: string }> {
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

