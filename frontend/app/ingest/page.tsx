"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useState } from "react"
import { Download, Loader2, CheckCircle, AlertCircle } from "lucide-react"

type IngestionStatus = "idle" | "loading" | "success" | "error"

export default function IngestPage() {
  const [huggingfaceUrl, setHuggingfaceUrl] = useState("")
  const [status, setStatus] = useState<IngestionStatus>("idle")
  const [message, setMessage] = useState("")

  const handleIngest = () => {
    setStatus("loading")
    // Simulate API call
    setTimeout(() => {
      if (huggingfaceUrl.includes("bert")) {
        setStatus("success")
        setMessage("Model ingested successfully! All quality metrics passed.")
      } else {
        setStatus("error")
        setMessage("Model ingestion failed. Quality score below minimum threshold (0.5).")
      }
    }, 2000)
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-3xl font-bold text-foreground mb-2">Ingest HuggingFace Model</h1>
          <p className="text-muted-foreground mb-8">Import models from HuggingFace Hub to your registry</p>

          <div className="grid gap-6">
            {/* Input Card */}
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6 space-y-4">
              <div>
                <label htmlFor="hf-url" className="block text-sm font-medium text-foreground mb-2">
                  HuggingFace Model URL
                </label>
                <Input
                  id="hf-url"
                  placeholder="https://huggingface.co/google-bert/bert-base-uncased"
                  value={huggingfaceUrl}
                  onChange={(e) => setHuggingfaceUrl(e.target.value)}
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
                disabled={!huggingfaceUrl || status === "loading"}
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

            {/* Status Messages */}
            {status === "success" && (
              <Card className="bg-chart-3/10 border-chart-3/30 backdrop-blur p-6 flex gap-3">
                <CheckCircle className="h-5 w-5 text-chart-3 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground mb-1">Success</p>
                  <p className="text-sm text-muted-foreground">{message}</p>
                </div>
              </Card>
            )}

            {status === "error" && (
              <Card className="bg-destructive/10 border-destructive/30 backdrop-blur p-6 flex gap-3">
                <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-foreground mb-1">Ingestion Failed</p>
                  <p className="text-sm text-muted-foreground">{message}</p>
                </div>
              </Card>
            )}

            {/* Info Card */}
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h2 className="font-semibold text-foreground mb-3">How It Works</h2>
              <ol className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <span className="font-semibold text-foreground">1.</span> Paste a HuggingFace model URL
                </li>
                <li>
                  <span className="font-semibold text-foreground">2.</span> We automatically analyze the model
                </li>
                <li>
                  <span className="font-semibold text-foreground">3.</span> Quality metrics are calculated
                </li>
                <li>
                  <span className="font-semibold text-foreground">4.</span> If all metrics pass, the model is ingested
                </li>
              </ol>
            </Card>
          </div>
        </div>
      </div>
    </main>
  )
}
