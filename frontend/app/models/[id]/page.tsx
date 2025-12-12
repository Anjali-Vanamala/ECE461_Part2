import { ModelDetailClient } from "./ModelDetailClient"

// Disable dynamic params for static export
export const dynamicParams = false

// Static export: generate placeholder route
// Actual model data is fetched client-side
export function generateStaticParams(): Array<{ id: string }> {
  return [{ id: "placeholder" }]
}

export default async function ModelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <ModelDetailClient id={id} />
}
