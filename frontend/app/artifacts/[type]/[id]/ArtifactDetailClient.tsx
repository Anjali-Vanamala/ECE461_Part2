"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { ArrowLeft, Download, Share2, Flag, Loader2 } from "lucide-react"
import { LineageGraph } from "@/components/lineage-graph"
import { ModelScoreCard } from "@/components/model-score-card"
import { useEffect, useState } from "react"
import { fetchArtifactById, fetchModelRating, API_BASE_URL, type ArtifactType } from "@/lib/api"

export function ArtifactDetailClient({ type, id }: { type: ArtifactType; id: string }) {
  const [artifact, setArtifact] = useState<any>(null)
  const [rating, setRating] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadArtifact() {
      if (!id || !type) {
        return
      }

      try {
        setLoading(true)
        const [artifactData, ratingData] = await Promise.all([
          fetchArtifactById(type, id),
          type === 'model' ? fetchModelRating(id).catch(() => null) : Promise.resolve(null), // Only models have ratings
        ])
        setArtifact(artifactData)
        setRating(ratingData)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : `Failed to load ${type}`)
        console.error(`Error loading ${type}:`, err)
      } finally {
        setLoading(false)
      }
    }

    loadArtifact()
  }, [id, type])

  if (loading) {
    return (
      <main className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading {type}...</span>
          </div>
        </div>
      </main>
    )
  }

  if (error || !artifact) {
    return (
      <main className="min-h-screen bg-background">
        <div className="container mx-auto px-4 py-8">
          <Button variant="ghost" asChild className="mb-6 gap-2">
            <Link href="/browse">
              <ArrowLeft className="h-4 w-4" />
              Back to Browse
            </Link>
          </Button>
          <Card className="bg-destructive/10 border-destructive/30 backdrop-blur p-6">
            <p className="text-destructive">Error: {error || `${type} not found`}</p>
          </Card>
        </div>
      </main>
    )
  }

  // Map backend data to frontend format
  const artifactName = artifact.metadata?.name || `Unknown ${type}`
  const artifactUrl = artifact.data?.url || ""
  const artifactType = artifact.metadata?.type || type
  
  // Only calculate scores for models
  const scores = type === 'model' && rating ? {
    overall: rating.net_score ? rating.net_score * 5 : 0,
    quality: rating.code_quality ? rating.code_quality * 5 : 0,
    reproducibility: rating.reproducibility ? rating.reproducibility : 0,
    reviewedness: rating.reviewedness ? rating.reviewedness : 0,
    treescore: rating.tree_score ? rating.tree_score * 5 : 0,
    documentation: rating.dataset_and_code_score ? rating.dataset_and_code_score * 5 : 0,
  } : {
    overall: 0,
    quality: 0,
    reproducibility: 0,
    reviewedness: 0,
    treescore: 0,
    documentation: 0,
  }

  const getSourceName = () => {
    if (artifactUrl.includes('huggingface.co')) {
      return 'HuggingFace'
    } else if (artifactUrl.includes('github.com')) {
      return 'GitHub'
    }
    return 'External'
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Back Button */}
        <Button variant="ghost" asChild className="mb-6 gap-2">
          <Link href="/browse">
            <ArrowLeft className="h-4 w-4" />
            Back to Browse
          </Link>
        </Button>

        {/* Header Section */}
        <div className="mb-8 flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="flex-1">
            <h1 className="text-4xl font-bold text-foreground">{artifactName}</h1>
            <p className="mt-2 text-muted-foreground">{type.charAt(0).toUpperCase() + type.slice(1)} ID: {id || "Loading..."}</p>
            {artifactUrl && (
              <p className="mt-1 text-sm text-muted-foreground">
                <a href={artifactUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  View on {getSourceName()}
                </a>
              </p>
            )}
          </div>

          <div className="flex flex-col gap-3 md:flex-row">
            <Button size="lg" asChild disabled={!id}>
              <a 
                href={id ? `${API_BASE_URL}/artifacts/${type}/${id}/download` : "#"} 
                className="gap-2"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Download className="h-4 w-4" />
                Download
              </a>
            </Button>
            <Button variant="outline" size="lg" className="gap-2 bg-transparent">
              <Share2 className="h-4 w-4" />
              Share
            </Button>
            <Button variant="outline" size="lg" className="gap-2 bg-transparent">
              <Flag className="h-4 w-4" />
              Report
            </Button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column - Description & Info */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h2 className="text-xl font-semibold text-foreground mb-4">About</h2>
              <p className="text-muted-foreground leading-relaxed">
                {artifactUrl ? (
                  <>
                    {type.charAt(0).toUpperCase() + type.slice(1)} URL: <a href={artifactUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{artifactUrl}</a>
                  </>
                ) : (
                  "No additional information available."
                )}
              </p>
            </Card>

            {/* Scores Section - Only for models */}
            {type === 'model' && (
              <div>
                <h2 className="text-xl font-semibold text-foreground mb-4">Scores & Metrics</h2>
                <div className="grid gap-4 md:grid-cols-2">
                  <ModelScoreCard label="Overall Rating" value={scores.overall} max={5} />
                  <ModelScoreCard label="Quality" value={scores.quality} max={5} />
                  <ModelScoreCard label="Reproducibility" value={scores.reproducibility} max={1} />
                  <ModelScoreCard label="Code Review" value={scores.reviewedness} max={1} percentage />
                  <ModelScoreCard label="Treescore" value={scores.treescore} max={5} />
                  <ModelScoreCard label="Documentation" value={scores.documentation} max={5} />
                </div>
              </div>
            )}

            {/* Lineage Section */}
            {artifact.lineage && (
              <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
                <h2 className="text-xl font-semibold text-foreground mb-4">Lineage</h2>
                <LineageGraph lineage={artifact.lineage.nodes?.map((n: any) => n.name) || []} />
              </Card>
            )}
          </div>

          {/* Right Column - Sidebar */}
          <div className="space-y-4">
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h3 className="font-semibold text-foreground mb-4">{type.charAt(0).toUpperCase() + type.slice(1)} Info</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-muted-foreground">{type.charAt(0).toUpperCase() + type.slice(1)} ID</p>
                  <p className="font-semibold text-foreground break-all">{id || "Loading..."}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Type</p>
                  <p className="font-semibold text-foreground">{artifactType}</p>
                </div>
                {artifactUrl && (
                  <div>
                    <p className="text-muted-foreground">Source</p>
                    <p className="font-semibold text-foreground break-all">
                      <a href={artifactUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                        {getSourceName()}
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
                  <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer">
                    View API Docs
                  </a>
                </Button>
                {artifactUrl && (
                  <Button variant="outline" className="w-full justify-start bg-transparent" asChild>
                    <a href={artifactUrl} target="_blank" rel="noopener noreferrer">
                      View on {getSourceName()}
                    </a>
                  </Button>
                )}
                {artifactUrl && artifactUrl.includes('github.com') && (
                  <Button variant="outline" className="w-full justify-start bg-transparent" asChild>
                    <a href={artifactUrl} target="_blank" rel="noopener noreferrer">
                      View GitHub
                    </a>
                  </Button>
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </main>
  )
}

