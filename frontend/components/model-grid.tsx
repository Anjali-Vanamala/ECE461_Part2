"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { Download, Star, GitBranch, Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { fetchModels, fetchModelRating } from "@/lib/api"

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

export function ModelGrid() {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadModels() {
      try {
        const artifacts = await fetchModels()
        
        // Fetch ratings for each model and map to frontend format
        const modelsWithRatings = await Promise.all(
          artifacts.slice(0, 6).map(async (artifact: any) => { // Limit to 6 for grid
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
              rating: rating?.overall_score ? rating.overall_score / 20 : 0,
              downloads: 0,
              reproducibility: rating?.reproducibility_score ? rating.reproducibility_score / 100 : 0,
              reviewedness: rating?.code_review_score ? rating.code_review_score / 100 : 0,
              treescore: rating?.treescore ? rating.treescore / 20 : 0,
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading models...</span>
      </div>
    )
  }

  if (models.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No models available</p>
      </div>
    )
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {models.map((model) => (
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
                <Link href={`/models/${model.id}`}>Details</Link>
              </Button>
              <Button asChild size="sm" className="flex-1">
                <Link href={`/models/${model.id}/download`}>Download</Link>
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
