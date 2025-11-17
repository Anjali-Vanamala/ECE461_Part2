"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { ArrowLeft, Download, Share2, Flag } from "lucide-react"
import { LineageGraph } from "@/components/lineage-graph"
import { ModelScoreCard } from "@/components/model-score-card"

// Required for static export with dynamic routes
// TEMPORARY: Using mock model IDs that match existing mock data in browse/page.tsx and model-grid.tsx
// This allows static export to build successfully.
// TODO: When integrating with real API, update this to:
//   - Fetch model IDs from API at build time (if API available during CI/CD build)
//   - Or remove static export and use server-side rendering if models are truly dynamic
export function generateStaticParams() {
  // These IDs match the mock data currently used throughout the frontend
  // See: frontend/app/browse/page.tsx and frontend/components/model-grid.tsx
  return [
    { id: "bert-base" },
    { id: "resnet-50" },
    { id: "gpt2-small" },
  ]
}

const mockModelDetail = {
  id: "bert-base",
  name: "BERT Base Uncased",
  version: "v2.1",
  author: "Google Research",
  description: "A transformer-based model pre-trained on English Wikipedia and BookCorpus",
  fullDescription:
    "BERT (Bidirectional Encoder Representations from Transformers) is a method of pre-training language representations that obtains state-of-the-art results on a wide array of Natural Language Processing tasks. This is the base uncased model, suitable for most NLP tasks.",
  tags: ["NLP", "Transformer", "Production", "Pre-trained"],
  size: "440 MB",
  downloads: 15420,
  lastUpdated: "2024-10-15",
  rating: 4.8,
  scores: {
    overall: 4.8,
    quality: 4.9,
    reproducibility: 1.0,
    reviewedness: 0.95,
    treescore: 4.7,
    documentation: 4.5,
    latency: 3.8,
  },
  lineage: ["BERT-pretrained", "Transformers v4.30", "Wikipedia Corpus v2022"],
}

export default function ModelDetailPage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Back Button */}
        <Button variant="ghost" asChild className="mb-6 gap-2">
          <Link href="/">
            <ArrowLeft className="h-4 w-4" />
            Back to Models
          </Link>
        </Button>

        {/* Header Section */}
        <div className="mb-8 flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="flex-1">
            <h1 className="text-4xl font-bold text-foreground">{mockModelDetail.name}</h1>
            <p className="mt-2 text-muted-foreground">{mockModelDetail.version}</p>
            <p className="mt-1 text-sm text-muted-foreground">By {mockModelDetail.author}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {mockModelDetail.tags.map((tag) => (
                <Badge key={tag}>{tag}</Badge>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 md:flex-row">
            <Button size="lg" asChild>
              <Link href={`/models/${params.id}/download`} className="gap-2">
                <Download className="h-4 w-4" />
                Download
              </Link>
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
              <p className="text-muted-foreground leading-relaxed">{mockModelDetail.fullDescription}</p>
            </Card>

            {/* Scores Section */}
            <div>
              <h2 className="text-xl font-semibold text-foreground mb-4">Scores & Metrics</h2>
              <div className="grid gap-4 md:grid-cols-2">
                <ModelScoreCard label="Overall Rating" value={mockModelDetail.scores.overall} max={5} />
                <ModelScoreCard label="Quality" value={mockModelDetail.scores.quality} max={5} />
                <ModelScoreCard label="Reproducibility" value={mockModelDetail.scores.reproducibility} max={1} />
                <ModelScoreCard label="Code Review" value={mockModelDetail.scores.reviewedness} max={1} percentage />
                <ModelScoreCard label="Treescore" value={mockModelDetail.scores.treescore} max={5} />
                <ModelScoreCard label="Documentation" value={mockModelDetail.scores.documentation} max={5} />
              </div>
            </div>

            {/* Lineage Section */}
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h2 className="text-xl font-semibold text-foreground mb-4">Lineage</h2>
              <LineageGraph lineage={mockModelDetail.lineage} />
            </Card>
          </div>

          {/* Right Column - Sidebar */}
          <div className="space-y-4">
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h3 className="font-semibold text-foreground mb-4">Model Info</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Model Size</p>
                  <p className="font-semibold text-foreground">{mockModelDetail.size}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Downloads</p>
                  <p className="font-semibold text-foreground">{mockModelDetail.downloads.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Last Updated</p>
                  <p className="font-semibold text-foreground">{mockModelDetail.lastUpdated}</p>
                </div>
              </div>
            </Card>

            <Card className="bg-card/40 border-border/50 backdrop-blur p-6">
              <h3 className="font-semibold text-foreground mb-4">Quick Actions</h3>
              <div className="space-y-2">
                <Button variant="outline" className="w-full justify-start bg-transparent">
                  View API Docs
                </Button>
                <Button variant="outline" className="w-full justify-start bg-transparent">
                  View on HuggingFace
                </Button>
                <Button variant="outline" className="w-full justify-start bg-transparent">
                  View GitHub
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </main>
  )
}
