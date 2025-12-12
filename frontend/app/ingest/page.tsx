"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useState } from "react"
import { Download, Loader2, CheckCircle, AlertCircle } from "lucide-react"
import { ingestArtifact, type ArtifactType } from "@/lib/api"

type IngestionStatus = "idle" | "loading" | "success" | "error"

export default function IngestPage() {
  const [artifactType, setArtifactType] = useState<ArtifactType>("model")
  const [url, setUrl] = useState("")
  const [status, setStatus] = useState<IngestionStatus>("idle")
  const [message, setMessage] = useState("")
  const [ingestedArtifactId, setIngestedArtifactId] = useState<string | null>(null)

  const handleIngest = async () => {
    if (!url.trim()) {
      setStatus("error")
      setMessage(`Please enter a ${artifactType} URL`)
      return
    }

    setStatus("loading")
    setMessage("")
    
    try {
      const result = await ingestArtifact(artifactType, url)
      setStatus("success")
      setIngestedArtifactId(result.metadata?.id || null)
      const artifactName = artifactType === "model" ? "Model" : artifactType === "dataset" ? "Dataset" : "Code"
      setMessage(`${artifactName} ingested successfully!`)
    } catch (error) {
      setStatus("error")
      const artifactName = artifactType === "model" ? "Model" : artifactType === "dataset" ? "Dataset" : "Code"
      setMessage(error instanceof Error ? error.message : `${artifactName} ingestion failed. Please check the URL and try again.`)
    }
  }

  const getPlaceholder = () => {
    switch (artifactType) {
      case "model":
        return "https://huggingface.co/google-bert/bert-base-uncased"
      case "dataset":
        return "https://huggingface.co/datasets/glue"
      case "code":
        return "https://github.com/huggingface/transformers"
      default:
        return "Enter URL"
    }
  }

  const getDescription = () => {
    switch (artifactType) {
      case "model":
        return "Import models from HuggingFace Hub to your registry"
      case "dataset":
        return "Import datasets from HuggingFace Hub to your registry"
      case "code":
        return "Import code repositories from GitHub to your registry"
      default:
        return "Import artifacts to your registry"
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-3xl font-bold text-foreground mb-2">Ingest Artifact</h1>
          <p className="text-muted-foreground mb-8">{getDescription()}</p>

          <Tabs value={artifactType} onValueChange={(v) => {
            setArtifactType(v as ArtifactType)
            setStatus("idle")
            setMessage("")
            setIngestedArtifactId(null)
            setUrl("")
          }}>
            <TabsList className="grid w-full grid-cols-3 mb-6">
              <TabsTrigger value="model">Model</TabsTrigger>
              <TabsTrigger value="dataset">Dataset</TabsTrigger>
              <TabsTrigger value="code">Code</TabsTrigger>
            </TabsList>

            <TabsContent value="model" className="space-y-6">
              <Card className="bg-card/40 border-border/50 backdrop-blur p-6 space-y-4">
                <div>
                  <label htmlFor="model-url" className="block text-sm font-medium text-foreground mb-2">
                    HuggingFace Model URL
                  </label>
                  <Input
                    id="model-url"
                    placeholder={getPlaceholder()}
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={status === "loading"}
                  />
                </div>

                <div className="rounded-lg bg-secondary/10 border border-secondary/20 p-4">
                  <p className="text-xs font-medium text-foreground mb-2">Quality Requirements</p>
                  <ul className="text-xs text-muted-foreground space-y-1">
                    <li>• Overall Score: ≥ 0.5</li>
                    <li>• Reproducibility: ≥ 0.5</li>
                    <li>• Code Review: ≥ 0.5</li>
                    <li>• Treescore: ≥ 0.5</li>
                  </ul>
                </div>

                <Button
                  onClick={handleIngest}
                  disabled={!url || status === "loading"}
                  className="w-full gap-2"
                >
                  {status === "loading" ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Ingesting...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4" />
                      Ingest Model
                    </>
                  )}
                </Button>
              </Card>
            </TabsContent>

            <TabsContent value="dataset" className="space-y-6">
              <Card className="bg-card/40 border-border/50 backdrop-blur p-6 space-y-4">
                <div>
                  <label htmlFor="dataset-url" className="block text-sm font-medium text-foreground mb-2">
                    HuggingFace Dataset URL
                  </label>
                  <Input
                    id="dataset-url"
                    placeholder={getPlaceholder()}
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={status === "loading"}
                  />
                </div>

                <Button
                  onClick={handleIngest}
                  disabled={!url || status === "loading"}
                  className="w-full gap-2"
                >
                  {status === "loading" ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Ingesting...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4" />
                      Ingest Dataset
                    </>
                  )}
                </Button>
              </Card>
            </TabsContent>

            <TabsContent value="code" className="space-y-6">
              <Card className="bg-card/40 border-border/50 backdrop-blur p-6 space-y-4">
                <div>
                  <label htmlFor="code-url" className="block text-sm font-medium text-foreground mb-2">
                    GitHub Repository URL
                  </label>
                  <Input
                    id="code-url"
                    placeholder={getPlaceholder()}
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={status === "loading"}
                  />
                </div>

                <Button
                  onClick={handleIngest}
                  disabled={!url || status === "loading"}
                  className="w-full gap-2"
                >
                  {status === "loading" ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Ingesting...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4" />
                      Ingest Code
                    </>
                  )}
                </Button>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Status Messages */}
          {status === "success" && (
            <Card className="bg-chart-3/10 border-chart-3/30 backdrop-blur p-6 flex gap-3 mt-6">
              <CheckCircle className="h-5 w-5 text-chart-3 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-foreground mb-1">Success</p>
                <p className="text-sm text-muted-foreground">{message}</p>
                {ingestedArtifactId && (
                  <p className="text-xs text-muted-foreground mt-2">
                    {artifactType === "model" ? "Model" : artifactType === "dataset" ? "Dataset" : "Code"} ID: {ingestedArtifactId}
                  </p>
                )}
              </div>
            </Card>
          )}

          {status === "error" && (
            <Card className="bg-destructive/10 border-destructive/30 backdrop-blur p-6 flex gap-3 mt-6">
              <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-foreground mb-1">Ingestion Failed</p>
                <p className="text-sm text-muted-foreground">{message}</p>
              </div>
            </Card>
          )}

          {/* Info Card */}
          <Card className="bg-card/40 border-border/50 backdrop-blur p-6 mt-6">
            <h2 className="font-semibold text-foreground mb-3">How It Works</h2>
            <ol className="space-y-2 text-sm text-muted-foreground">
              <li>
                <span className="font-semibold text-foreground">1.</span> Select the artifact type (Model, Dataset, or Code)
              </li>
              <li>
                <span className="font-semibold text-foreground">2.</span> Paste the URL (HuggingFace for models/datasets, GitHub for code)
              </li>
              <li>
                <span className="font-semibold text-foreground">3.</span> We automatically analyze the artifact
              </li>
              <li>
                <span className="font-semibold text-foreground">4.</span> {artifactType === "model" ? "Quality metrics are calculated and if all metrics pass, " : ""}The artifact is ingested
              </li>
            </ol>
          </Card>
        </div>
      </div>
    </main>
  )
}
