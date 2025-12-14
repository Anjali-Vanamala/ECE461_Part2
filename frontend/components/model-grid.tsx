"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { Download, Star, GitBranch, Loader2 } from "lucide-react"
import { useEffect, useState, useMemo } from "react"
import { fetchModels, fetchModelRating, API_BASE_URL } from "@/lib/api"

interface Model {
  id: string
  name: string
  version: string
  description: string
  rating: number
  downloads: number
  reproducibility: number
  reviewedness: number
  treescore: number
  tags: string[]
}

export type ViewMode = "grid" | "list"

interface ModelGridProps {
  searchQuery?: string
  viewMode?: ViewMode
}

export function ModelGrid({ searchQuery = "", viewMode = "grid" }: ModelGridProps) {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadModels() {
      try {
        const artifacts = await fetchModels()
        
        // Fetch ratings for each model and map to frontend format
        const modelsWithRatings = await Promise.all(
          artifacts.map(async (artifact: any) => {
            let rating = null
            try {
              rating = await fetchModelRating(artifact.id)
            } catch (e) {
              // Rating might not exist, that's okay
            }

            return {
              id: artifact.id,
              name: artifact.name,
              version: "v1.0", // Not available in backend
              description: "", // Not available in artifact metadata
              rating: rating?.net_score ? rating.net_score * 5 : 0, // net_score is 0-1, convert to 0-5
              downloads: 0,
              reproducibility: rating?.reproducibility ? rating.reproducibility : 0, // reproducibility is 0-1
              reviewedness: rating?.reviewedness ? rating.reviewedness : 0, // reviewedness is 0-1
              treescore: rating?.tree_score ? rating.tree_score * 5 : 0, // tree_score is 0-1, convert to 0-5
              tags: [],
            } as Model
          })
        )
        
        setModels(modelsWithRatings)
      } catch (err) {
        console.error("Error loading models:", err)
      } finally {
        setLoading(false)
      }
    }

    loadModels()
  }, [])

  // Filter models based on search query (memoized for performance)
  const displayModels = useMemo(() => {
    const filtered = models.filter((model) => {
      if (!searchQuery.trim()) {
        return true
      }
      const query = searchQuery.toLowerCase()
      return model.name.toLowerCase().includes(query) ||
             model.description.toLowerCase().includes(query) ||
             model.tags.some(tag => tag.toLowerCase().includes(query))
    })
    // Limit to 6 for grid display (after filtering)
    return filtered.slice(0, 6)
  }, [models, searchQuery])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading models...</span>
      </div>
    )
  }

  if (displayModels.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">
          {searchQuery ? `No models found matching "${searchQuery}"` : "No models available"}
        </p>
      </div>
    )
  }

  if (viewMode === "list") {
    return (
      <div className="space-y-3">
        {displayModels.map((model) => (
          <Card
            key={model.id}
            className="bg-card/40 border-border/50 backdrop-blur p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:border-primary/50 transition-all"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-lg font-semibold text-foreground">{model.name}</h3>
                <div className="flex items-center gap-1">
                  <Star className="h-4 w-4 fill-chart-2 text-chart-2" />
                  <span className="text-sm font-medium">{model.rating.toFixed(1)}</span>
                </div>
              </div>
              <p className="text-sm text-muted-foreground mb-2 line-clamp-1">{model.description || "No description available"}</p>
              <div className="flex flex-wrap gap-2">
                {model.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-6 text-xs text-muted-foreground md:justify-end">
              <span className="flex items-center gap-1">
                <Download className="h-3 w-3" />
                {model.downloads.toLocaleString()}
              </span>
              <span>Repro: {(model.reproducibility * 100).toFixed(0)}%</span>
              <span className="flex items-center gap-1">
                <GitBranch className="h-3 w-3" />
                Tree: {model.treescore.toFixed(1)}
              </span>
            </div>

            <div className="flex gap-2 md:ml-auto">
              <Button asChild variant="outline" size="sm" className="bg-transparent">
                <Link 
                  href={`/artifacts/model/${model.id}`} 
                  aria-label={`View details for ${model.name}`}
                >
                  Details
                </Link>
              </Button>
              <Button asChild size="sm">
                <a 
                  href={`${API_BASE_URL}/artifacts/model/${model.id}/download`} 
                  aria-label={`Download ${model.name}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Download
                </a>
              </Button>
            </div>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {displayModels.map((model) => (
        <Card
          key={model.id}
          className="flex flex-col overflow-hidden border-border/50 bg-card/40 backdrop-blur hover:border-primary/50 hover:shadow-lg transition-all duration-300"
        >
          <div className="flex-1 p-6">
            <div className="mb-3 flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-foreground">{model.name}</h3>
                <p className="text-xs text-muted-foreground">{model.version}</p>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-1">
                  <Star className="h-4 w-4 fill-chart-2 text-chart-2" />
                  <span className="text-sm font-medium">{model.rating}</span>
                </div>
              </div>
            </div>

            <p className="mb-4 line-clamp-2 text-sm text-muted-foreground">{model.description}</p>

            <div className="mb-4 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded bg-secondary/20 p-2">
                <p className="text-muted-foreground">Reproducibility</p>
                <p className="font-semibold text-foreground">{(model.reproducibility * 100).toFixed(0)}%</p>
              </div>
              <div className="rounded bg-secondary/20 p-2">
                <p className="text-muted-foreground">Reviewed</p>
                <p className="font-semibold text-foreground">{(model.reviewedness * 100).toFixed(0)}%</p>
              </div>
            </div>

            <div className="mb-4 flex flex-wrap gap-2">
              {model.tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>

            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Download className="h-3 w-3" />
                {model.downloads.toLocaleString()}
              </span>
              <span className="flex items-center gap-1">
                <GitBranch className="h-3 w-3" />
                Tree: {model.treescore.toFixed(1)}
              </span>
            </div>
          </div>

          <div className="border-t border-border/50 bg-card/80 p-4">
            <div className="flex gap-2">
              <Button asChild variant="outline" size="sm" className="flex-1 bg-transparent">
                <Link 
                  href={`/artifacts/model/${model.id}`} 
                  aria-label={`View details for ${model.name}`}
                >
                  Details
                </Link>
              </Button>
              <Button asChild size="sm" className="flex-1">
                <a 
                  href={`${API_BASE_URL}/artifacts/model/${model.id}/download`} 
                  aria-label={`Download ${model.name}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Download
                </a>
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
