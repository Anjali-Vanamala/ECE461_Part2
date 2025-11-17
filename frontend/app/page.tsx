import { SearchModels } from "@/components/search-models"
import { ModelGrid } from "@/components/model-grid"
import { StatsOverview } from "@/components/stats-overview"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <StatsOverview />
        <SearchModels />
        <ModelGrid />
      </div>
    </main>
  )
}
