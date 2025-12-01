"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { useState, useEffect } from "react"
import { Search, Download, Star, Loader2 } from "lucide-react"
import { fetchModels, fetchModelRating } from "@/lib/api"

interface BrowseModel {
  id: string
  name: string
  rating: number
  downloads: number
  reproducibility: number
  reviewedness: number
  tags: string[]
}

export default function BrowsePage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [models, setModels] = useState<BrowseModel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadModels() {
      try {
        setLoading(true)
        const artifacts = await fetchModels()
        
        // Fetch ratings for each model
        const modelsWithRatings = await Promise.all(
          artifacts.map(async (artifact: any) => {
            let rating = null
            try {
              rating = await fetchModelRating(artifact.id)
            } catch (e) {
              // Rating might not exist, that's okay
            }

            // Map backend artifact to frontend model format
            const model: BrowseModel = {
              id: artifact.id,
              name: artifact.name,
              rating: rating?.overall_score ? rating.overall_score / 20 : 0, // Convert 0-100 to 0-5 scale
              downloads: 0, // Not available in backend
              reproducibility: rating?.reproducibility_score ? rating.reproducibility_score / 100 : 0,
              reviewedness: rating?.code_review_score ? rating.code_review_score / 100 : 0,
              tags: [], // Not available in backend artifact metadata
            }
            return model
          })
        )
        
        setModels(modelsWithRatings)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load models")
        console.error("Error loading models:", err)
      } finally {
        setLoading(false)
      }
    }

    loadModels()
  }, [])

  const filteredModels = models.filter((model) => {
    const matchesSearch = model.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTag = !selectedTag || model.tags.includes(selectedTag)
    return matchesSearch && matchesTag
  })

  return (
    <main id="main-content" className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <header>
          <h1 className="text-3xl font-bold text-foreground mb-2">Browse Models</h1>
          <p className="text-muted-foreground mb-8">Discover trusted machine learning models</p>
        </header>

        {/* Search */}
        <section aria-label="Search and filter" className="mb-8 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input
              id="search-models"
              aria-label="Search models"
              placeholder="Search models..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Tag Filters */}
          <div className="flex flex-wrap gap-2">
            {["NLP", "Vision", "Audio", "Production", "Fine-tuned"].map((tag) => (
              <button
                key={tag}
                onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                aria-pressed={selectedTag === tag}
                aria-label={`Filter by ${tag} tag`}
                className={`rounded-full px-3 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
                  selectedTag === tag
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary/30 text-foreground hover:bg-secondary/50 dark:hover:bg-secondary/70"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </section>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12" role="status" aria-live="polite" aria-busy="true">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
            <span className="ml-2 text-muted-foreground">Loading models...</span>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <Card className="bg-destructive/10 border-destructive/30 backdrop-blur p-6" role="alert" aria-live="assertive">
            <p className="text-destructive">Error: {error}</p>
          </Card>
        )}

        {/* Models List */}
        {!loading && !error && (
          <section aria-label="Model listings" className="space-y-3">
            {filteredModels.length === 0 ? (
              <Card className="bg-card/40 border-border/50 backdrop-blur p-6 text-center">
                <p className="text-muted-foreground">No models found</p>
              </Card>
            ) : (
              filteredModels.map((model) => (
            <Card
              key={model.id}
              className="bg-card/40 border-border/50 backdrop-blur p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:border-primary/50 hover:bg-card/60 hover:shadow-lg transition-all"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h2 className="text-lg font-semibold text-foreground">{model.name}</h2>
                  <div className="flex items-center gap-1">
                    <Star className="h-4 w-4 fill-chart-2 text-chart-2" aria-hidden="true" />
                    <span className="text-sm font-medium" aria-label={`Rating: ${model.rating} out of 5`}>{model.rating}</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {model.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-6 text-xs text-muted-foreground md:justify-end">
                <span className="flex items-center gap-1" aria-label={`${model.downloads.toLocaleString()} downloads`}>
                  <Download className="h-3 w-3" aria-hidden="true" />
                  {model.downloads.toLocaleString()}
                </span>
                <span aria-label={`Reproducibility: ${(model.reproducibility * 100).toFixed(0)}%`}>Repro: {(model.reproducibility * 100).toFixed(0)}%</span>
              </div>

              <div className="flex gap-2 md:ml-auto">
                <Button asChild variant="outline" size="sm">
                  <Link href={`/models/${model.id}`}
                        aria-label={`View details for ${model.name}`}
                        >Details</Link>
                </Button>
                <Button asChild size="sm">
                  <Link href={`/models/${model.id}/download`}
                        aria-label={`Download ${model.name}`}>Download</Link>
                </Button>
              </div>
            </Card>
              ))
            )}
          </section>
        )}
      </div>
    </main>
  )
}
