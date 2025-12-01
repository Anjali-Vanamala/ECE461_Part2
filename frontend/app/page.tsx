import { SearchModels } from "@/components/search-models"
import { ModelGrid } from "@/components/model-grid"
import { StatsOverview } from "@/components/stats-overview"

export default function Home() {
  return (
    <main id="main-content" className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <h1 className="sr-only">Model Registry Dashboard</h1>
        <section aria-label="Statistics overview">
          <StatsOverview />
        </section>
        <section aria-label="Search and filter models">
          <SearchModels />
        </section>
        <section aria-label="Model grid">
          <ModelGrid />
        </section>
      </div>
    </main>
  )
}
