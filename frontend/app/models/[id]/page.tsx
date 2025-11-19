import { ModelDetailClient } from "./ModelDetailClient"

// For static export, we need to return at least one param so the route structure exists
// The client component will handle fetching data for any model ID at runtime
export function generateStaticParams(): Array<{ id: string }> {
  // Return a placeholder ID so the route structure is generated
  // The actual model data is fetched client-side, so any ID will work
  return [{ id: "placeholder" }]
}

export default function ModelDetailPage({ params }: { params: { id: string } }) {
  return <ModelDetailClient id={params.id} />
}
