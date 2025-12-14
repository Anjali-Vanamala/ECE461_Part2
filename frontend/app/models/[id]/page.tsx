import { ModelDetailClient } from "./ModelDetailClient"

// Enable dynamic routes for Amplify deployment
export const dynamicParams = true
export const dynamic = 'force-dynamic'

export default async function ModelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <ModelDetailClient id={id} />
}
