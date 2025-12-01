"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { ArrowLeft, Download, Share2, Flag, Loader2 } from "lucide-react"
import { LineageGraph } from "@/components/lineage-graph"
import { ModelScoreCard } from "@/components/model-score-card"
import { useEffect, useState } from "react"
import { fetchModelById, fetchModelRating, API_BASE_URL } from "@/lib/api"

export function ModelDetailClient({ id }: { id: string }) {
  const [model, setModel] = useState<any>(null)
  const [rating, setRating] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadModel() {
      if (!id) {
        return
      }

      try {
        setLoading(true)
        const [modelData, ratingData] = await Promise.all([
          fetchModelById(id),
          fetchModelRating(id).catch(() => null), // Rating might not exist
        ])
        setModel(modelData)
        setRating(ratingData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load model")
        console.error("Error loading model:", err)
      } finally {
        setLoading(false)
      }
    }

    loadModel()
  }, [id])

  if (loading) {
    return (
      <main className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center py-12" role="status" aria-live="polite" aria-busy="true">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
            <span className="ml-2 text-muted-foreground">Loading model...</span>
          </div>
        </div>
      </main>
    )
  }

  if (error || !model) {
    return (
      <main className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <Button variant="ghost" asChild className="mb-6 gap-2">
            <Link href="/">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to Models
            </Link>
          </Button>
          <Card className="bg-destructive/10 border-destructive/30 backdrop-blur p-6">
            <p className="text-destructive">Error: {error || "Model not found"}</p>
          </Card>
        </div>
      </main>
    )
  }

  // Map backend data to frontend format
  const modelName = model.metadata?.name || "Unknown Model"
  const modelUrl = model.data?.url || ""
  const scores = rating ? {
    overall: rating.overall_score ? rating.overall_score / 20 : 0,
    quality: rating.quality_score ? rating.quality_score / 20 : 0,
    reproducibility: rating.reproducibility_score ? rating.reproducibility_score / 100 : 0,
    reviewedness: rating.code_review_score ? rating.code_review_score / 100 : 0,
    treescore: rating.treescore ? rating.treescore / 20 : 0,
    documentation: rating.documentation_score ? rating.documentation_score / 20 : 0,
  } : {
    overall: 0,
    quality: 0,
    reproducibility: 0,
    reviewedness: 0,
    treescore: 0,
    documentation: 0,
  }
  return (
    <main id="main-content" className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Back Button */}
        <nav aria-label="Breadcrumb">
          <Button variant="ghost" asChild className="mb-6 gap-2">
            <Link href="/">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to Models
            </Link>
          </Button>
        </nav>

        {/* Header Section */}
        <header className="mb-8 flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="flex-1">
            <h1 className="text-4xl font-bold text-foreground">{modelName}</h1>
            <p className="mt-2 text-muted-foreground">Model ID: {id || "Loading..."}</p>
            {modelUrl && (
              <p className="mt-1 text-sm text-muted-foreground">
                <a href={modelUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline" aria-label="View on HuggingFace (opens in new tab)">
                  View on HuggingFace
                </a>
              </p>
            )}
          </div>

          <div className="flex flex-col gap-3 md:flex-row">
            <Button size="lg" asChild disabled={!id}>
              <Link href={id ? `/models/${id}/download` : "#"} className="gap-2">
                <Download className="h-4 w-4" aria-hidden="true" />
                Download
              </Link>
            </Button>
            <Button variant="outline" size="lg" className="gap-2 bg-transparent" aria-label="Share model">
              <Share2 className="h-4 w-4" aria-hidden="true" />
              Share
            </Button>
            <Button variant="outline" size="lg" className="gap-2 bg-transparent" aria-label="Report model">
              <Flag className="h-4 w-4" aria-hidden="true" />
              Report
            </Button>
          </div>
        </header>

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column - Description & Info */}
          <section className="lg:col-span-2 space-y-6" aria-label="Model details">
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h2 className="text-xl font-semibold text-foreground mb-4">About</h2>
              <p className="text-muted-foreground leading-relaxed">
                {modelUrl ? (
                  <>
                    Model URL: <a href={modelUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline" aria-label={`Model URL: ${modelUrl} (opens in new tab)`}>{modelUrl}</a>
                  </>
                ) : (
                  "No additional information available."
                )}
              </p>
            </Card>

            {/* Scores Section */}
            <section aria-label="Model scores and metrics">
              <h2 className="text-xl font-semibold text-foreground mb-4">Scores & Metrics</h2>
              <div className="grid gap-4 md:grid-cols-2">
                <ModelScoreCard label="Overall Rating" value={scores.overall} max={5} />
                <ModelScoreCard label="Quality" value={scores.quality} max={5} />
                <ModelScoreCard label="Reproducibility" value={scores.reproducibility} max={1} />
                <ModelScoreCard label="Code Review" value={scores.reviewedness} max={1} percentage />
                <ModelScoreCard label="Treescore" value={scores.treescore} max={5} />
                <ModelScoreCard label="Documentation" value={scores.documentation} max={5} />
              </div>
            </section>

            {/* Lineage Section */}
            {model.lineage && (
              <section aria-label="Model lineage">
                <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
                  <h2 className="text-xl font-semibold text-foreground mb-4">Lineage</h2>
                  <LineageGraph lineage={model.lineage.nodes?.map((n: any) => n.name) || []} />
                </Card>
              </section>
            )}
          </section>

          {/* Right Column - Sidebar */}
          <aside className="space-y-4" aria-label="Model information sidebar">
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h3 className="font-semibold text-foreground mb-4">Model Info</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Model ID</p>
                  <p className="font-semibold text-foreground break-all">{id || "Loading..."}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Type</p>
                  <p className="font-semibold text-foreground">{model.metadata?.type || "N/A"}</p>
                </div>
                {modelUrl && (
                  <div>
                    <p className="text-muted-foreground">Source</p>
                    <p className="font-semibold text-foreground break-all">
                      <a href={modelUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline" aria-label="View on HuggingFace (opens in new tab)">
                        HuggingFace
                      </a>
                    </p>
                  </div>
                )}
              </div>
            </Card>

            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h3 className="font-semibold text-foreground mb-4">Quick Actions</h3>
              <div className="space-y-2">
                <Button variant="outline" className="w-full justify-start bg-transparent" asChild>
                  <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer" aria-label="View API Docs (opens in new tab)">
                    View API Docs
                  </a>
                </Button>
                {modelUrl && (
                  <Button variant="outline" className="w-full justify-start bg-transparent" asChild>
                    <a href={modelUrl} target="_blank" rel="noopener noreferrer" aria-label="View on HuggingFace (opens in new tab)">
                      View on HuggingFace
                    </a>
                  </Button>
                )}
                <Button variant="outline" className="w-full justify-start bg-transparent" aria-label="View GitHub repository">
                  View GitHub
                </Button>
              </div>
            </Card>
          </aside>
        </div>
      </div>
    </main>
  )
}

