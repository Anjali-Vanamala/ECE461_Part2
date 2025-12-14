import { ArtifactDetailClient } from "./ArtifactDetailClient"

// Enable dynamic routes for Amplify deployment
export const dynamicParams = true

export default async function ArtifactDetailPage({ params }: { params: Promise<{ type: string; id: string }> }) {
  const { type, id } = await params

  // Validate type
  if (!['model', 'dataset', 'code'].includes(type)) {
    throw new Error(`Invalid artifact type: ${type}`)
  }

  return <ArtifactDetailClient type={type as 'model' | 'dataset' | 'code'} id={id} />
}

