import { ArtifactDetailClient } from "./ArtifactDetailClient"
import { notFound } from "next/navigation"

// Enable dynamic routes for Amplify deployment
export const dynamicParams = true
export const dynamic = 'force-dynamic'

export default async function ArtifactDetailPage({ params }: { params: Promise<{ type: string; id: string }> }) {
  const { type, id } = await params

  // Validate type
  if (!['model', 'dataset', 'code'].includes(type)) {
    notFound()
  }

  return <ArtifactDetailClient type={type as 'model' | 'dataset' | 'code'} id={id} />
}

