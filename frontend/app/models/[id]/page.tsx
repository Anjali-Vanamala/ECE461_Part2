import { ModelDetailClient } from "./ModelDetailClient"

// Allow dynamic params for this route
export const dynamicParams = true

// For static export builds, generate a placeholder param
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
