"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { Download, Star, GitBranch } from "lucide-react"

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

const mockModels: Model[] = [
  {
    id: "bert-base",
    name: "BERT Base Uncased",
    version: "v2.1",
    description: "A transformer-based model pre-trained on English Wikipedia and BookCorpus",
    rating: 4.8,
    downloads: 15420,
    reproducibility: 1,
    reviewedness: 0.95,
    treescore: 4.7,
    tags: ["NLP", "Transformer", "Production"],
  },
  {
    id: "resnet-50",
    name: "ResNet-50",
    version: "v1.0",
    description: "Deep residual network with 50 layers for image classification",
    rating: 4.6,
    downloads: 12340,
    reproducibility: 1,
    reviewedness: 0.88,
    treescore: 4.5,
    tags: ["Vision", "CNN", "Production"],
  },
  {
    id: "gpt2-small",
    name: "GPT-2 Small",
    version: "v1.0",
    description: "A smaller variant of GPT-2 language model for text generation",
    rating: 4.4,
    downloads: 9876,
    reproducibility: 0.5,
    reviewedness: 0.72,
    treescore: 4.3,
    tags: ["NLP", "Language Model", "Fine-tuning"],
  },
  {
    id: "wav2vec",
    name: "Wav2Vec 2.0",
    version: "v1.1",
    description: "Self-supervised learning model for speech recognition and audio tasks",
    rating: 4.5,
    downloads: 5432,
    reproducibility: 1,
    reviewedness: 0.91,
    treescore: 4.4,
    tags: ["Audio", "Speech", "Production"],
  },
]

export function ModelGrid() {
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {mockModels.map((model) => (
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
                  href={`/models/${model.id}`} 
                  aria-label={`View details for ${model.name}`}
                >
                  Details
                </Link>
              </Button>
              <Button asChild size="sm" className="flex-1">
                <Link 
                  href={`/models/${model.id}/download`} 
                  aria-label={`Download ${model.name}`}
                >
                  Download
                </Link>
              </Button>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
