"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import Link from "next/link"
import { useState, useEffect } from "react"
import { Search, Download, Star, Loader2, Grid3x3, List } from "lucide-react"
import { fetchArtifacts, fetchModelRating, API_BASE_URL, type ArtifactType } from "@/lib/api"

export type ViewMode = "grid" | "list"

interface BrowseArtifact {
  id: string
  name: string
  type: ArtifactType
  rating: number
  downloads: number
  reproducibility: number
  reviewedness: number
  tags: string[]
}

export default function BrowsePage() {
  const [artifactType, setArtifactType] = useState<ArtifactType>("model")
  const [searchQuery, setSearchQuery] = useState("")
  const [viewMode, setViewMode] = useState<ViewMode>("list")
  const [artifacts, setArtifacts] = useState<BrowseArtifact[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadArtifacts() {
      try {
        setLoading(true)
        const fetchedArtifacts = await fetchArtifacts(artifactType)
        
        // Fetch ratings for models only (datasets and code don't have ratings)
        const artifactsWithRatings = await Promise.all(
          fetchedArtifacts.map(async (artifact: any) => {
            let rating = null
            if (artifact.type === 'model') {
            try {
              rating = await fetchModelRating(artifact.id)
            } catch (e) {
              // Rating might not exist, that's okay
              }
            }

            // Map backend artifact to frontend format
            const browseArtifact: BrowseArtifact = {
              id: artifact.id,
              name: artifact.name,
              type: artifact.type,
              rating: rating?.net_score ? rating.net_score * 5 : 0, // net_score is 0-1, convert to 0-5
              downloads: 0, // Not available in backend
              reproducibility: rating?.reproducibility ? rating.reproducibility : 0, // reproducibility is 0-1
              reviewedness: rating?.reviewedness ? rating.reviewedness : 0, // reviewedness is 0-1
              tags: [], // Not available in backend artifact metadata
            }
            return browseArtifact
          })
        )
        
        setArtifacts(artifactsWithRatings)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load artifacts")
        console.error("Error loading artifacts:", err)
      } finally {
        setLoading(false)
      }
    }

    loadArtifacts()
  }, [artifactType])

  const filteredArtifacts = artifacts.filter((artifact) => {
    const matchesSearch = artifact.name.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSearch
  })

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Browse Artifacts</h1>
        <p className="text-muted-foreground mb-8">Discover models, datasets, and code repositories</p>

        <Tabs value={artifactType} onValueChange={(v) => setArtifactType(v as ArtifactType)}>
          <TabsList>
            <TabsTrigger value="model" id="tab-model-trigger" aria-controls="tab-model-content">
              Models
            </TabsTrigger>
            <TabsTrigger value="dataset" id="tab-dataset-trigger" aria-controls="tab-dataset-content">
              Datasets
            </TabsTrigger>
            <TabsTrigger value="code" id="tab-code-trigger" aria-controls="tab-code-content">
              Code
            </TabsTrigger>
          </TabsList>

          <TabsContent value="model" id="tab-model-content" aria-labelledby="tab-model-trigger">
            {/* Model content here */}
          </TabsContent>
          <TabsContent value="dataset" id="tab-dataset-content" aria-labelledby="tab-dataset-trigger">
            {/* Dataset content here */}
          </TabsContent>
          <TabsContent value="code" id="tab-code-content" aria-labelledby="tab-code-trigger">
            {/* Code content here */}
          </TabsContent>
        </Tabs>

        {/* Search and View Toggle */}
        <div className="mb-8">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
            <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
                id="search-artifacts"
                aria-label="Search artifacts"
                placeholder={`Search ${artifactType}s...`}
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
            <div className="flex gap-2">
              <Button
                variant={viewMode === "grid" ? "default" : "outline"}
                size="icon"
                onClick={() => setViewMode("grid")}
                aria-label="Grid view"
                className="bg-transparent"
              >
                <Grid3x3 className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "list" ? "default" : "outline"}
                size="icon"
                onClick={() => setViewMode("list")}
                aria-label="List view"
                className="bg-transparent"
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading models...</span>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <Card className="bg-destructive/10 border-destructive/30 backdrop-blur p-6">
            <p className="text-destructive">Error: {error}</p>
          </Card>
        )}

        {/* Artifacts List/Grid */}
        {!loading && !error && (
          <>
            {filteredArtifacts.length === 0 ? (
              <Card className="bg-card/40 border-border/50 backdrop-blur p-6 text-center">
                <p className="text-muted-foreground">No {artifactType}s found</p>
              </Card>
            ) : viewMode === "grid" ? (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {filteredArtifacts.map((artifact) => (
                  <Card
                    key={artifact.id}
                    className="flex flex-col overflow-hidden border-border/50 bg-card/40 backdrop-blur hover:border-primary/50 hover:shadow-lg transition-all duration-300"
                  >
                    <div className="flex-1 p-6">
                      <div className="mb-3 flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-foreground">{artifact.name}</h3>
                          <Badge variant="secondary" className="text-xs mt-1">
                            {artifact.type}
                          </Badge>
                        </div>
                        {artifact.type === 'model' && (
                          <div className="text-right">
                            <div className="flex items-center gap-1">
                              <Star className="h-4 w-4 fill-chart-2 text-chart-2" />
                              <span className="text-sm font-medium">{artifact.rating.toFixed(1)}</span>
                            </div>
                          </div>
                        )}
                      </div>

                      {artifact.type === 'model' && (
                        <>
                          <div className="mb-4 grid grid-cols-2 gap-2 text-xs">
                            <div className="rounded bg-secondary/20 p-2">
                              <p className="text-muted-foreground">Reproducibility</p>
                              <p className="font-semibold text-foreground">{(artifact.reproducibility * 100).toFixed(0)}%</p>
                            </div>
                            <div className="rounded bg-secondary/20 p-2">
                              <p className="text-muted-foreground">Reviewed</p>
                              <p className="font-semibold text-foreground">{(artifact.reviewedness * 100).toFixed(0)}%</p>
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-xs text-muted-foreground mb-4">
                            <span className="flex items-center gap-1">
                              <Download className="h-3 w-3" />
                              {artifact.downloads.toLocaleString()}
                            </span>
                          </div>
                        </>
                      )}

                      <div className="flex flex-wrap gap-2">
                        {artifact.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="border-t border-border/50 bg-card/80 p-4">
                      <div className="flex gap-2">
                        <Button asChild variant="outline" size="sm" className="flex-1 bg-transparent">
                          <Link 
                            href={`/artifacts/${artifact.type}/${artifact.id}`} 
                            aria-label={`View details for ${artifact.name}`}
                          >
                            Details
                          </Link>
                        </Button>
                        <Button asChild size="sm" className="flex-1">
                          <a 
                            href={`${API_BASE_URL}/artifacts/${artifact.type}/${artifact.id}/download`} 
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`Download ${artifact.name}`}
                          >
                            Download
                          </a>
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {filteredArtifacts.map((artifact) => (
            <Card
                    key={artifact.id}
              className="bg-card/40 border-border/50 backdrop-blur p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:border-primary/50 transition-all"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                        <h2 className="text-lg font-semibold text-foreground">{artifact.name}</h2>
                        {artifact.type === 'model' && (
                  <div className="flex items-center gap-1">
                    <Star className="h-4 w-4 fill-chart-2 text-chart-2" />
                            <span className="text-sm font-medium">{artifact.rating.toFixed(1)}</span>
                  </div>
                        )}
                </div>
                <div className="flex flex-wrap gap-2">
                        <Badge variant="secondary" className="text-xs">
                          {artifact.type}
                        </Badge>
                        {artifact.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>

                    {artifact.type === 'model' && (
              <div className="flex items-center gap-6 text-xs text-muted-foreground md:justify-end">
                <span className="flex items-center gap-1">
                  <Download className="h-3 w-3" />
                          {artifact.downloads.toLocaleString()}
                </span>
                        <span>Repro: {(artifact.reproducibility * 100).toFixed(0)}%</span>
              </div>
                    )}

              <div className="flex gap-2 md:ml-auto">
                <Button asChild variant="outline" size="sm">
                        <Link href={`/artifacts/${artifact.type}/${artifact.id}`}
                              aria-label={`View details for ${artifact.name}`}
                        >Details</Link>
                </Button>
                <Button asChild size="sm">
                        <a 
                          href={`${API_BASE_URL}/artifacts/${artifact.type}/${artifact.id}/download`}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Download ${artifact.name}`}
                        >
                          Download
                        </a>
                </Button>
              </div>
            </Card>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  )
}
