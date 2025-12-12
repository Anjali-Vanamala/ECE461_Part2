import { ModelDetailClient } from "./ModelDetailClient"

// For static export builds, generate a placeholder param
// Note: dynamicParams is false by default with output: 'export'
// In development, this route will be fully dynamic
export function generateStaticParams(): Array<{ id: string }> {
  // Return a placeholder ID so the route structure is generated for static export
  // The actual model data is fetched client-side, so any ID will work
  return [{ id: "placeholder" }]
}

export default async function ModelDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <ModelDetailClient id={id} />
}
