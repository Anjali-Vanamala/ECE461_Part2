"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { useState } from "react"
import { Search, Download, Star } from "lucide-react"

interface BrowseModel {
  id: string
  name: string
  rating: number
  downloads: number
  reproducibility: number
  reviewedness: number
  tags: string[]
}

const models: BrowseModel[] = [
  {
    id: "bert-base",
    name: "BERT Base Uncased",
    rating: 4.8,
    downloads: 15420,
    reproducibility: 1,
    reviewedness: 0.95,
    tags: ["NLP", "Transformer", "Production"],
  },
  {
    id: "resnet-50",
    name: "ResNet-50",
    rating: 4.6,
    downloads: 12340,
    reproducibility: 1,
    reviewedness: 0.88,
    tags: ["Vision", "CNN", "Production"],
  },
  {
    id: "gpt2-small",
    name: "GPT-2 Small",
    rating: 4.4,
    downloads: 9876,
    reproducibility: 0.5,
    reviewedness: 0.72,
    tags: ["NLP", "Language Model"],
  },
]

export default function BrowsePage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedTag, setSelectedTag] = useState<string | null>(null)

  const filteredModels = models.filter((model) => {
    const matchesSearch = model.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTag = !selectedTag || model.tags.includes(selectedTag)
    return matchesSearch && matchesTag
  })

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">Browse Models</h1>
        <p className="text-muted-foreground mb-8">Discover trusted machine learning models</p>

        {/* Search */}
        <div className="mb-8 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
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
                className={`rounded-full px-3 py-1 text-xs transition-colors ${
                  selectedTag === tag
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary/30 text-foreground hover:bg-secondary/50"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Models List */}
        <div className="space-y-3">
          {filteredModels.map((model) => (
            <Card
              key={model.id}
              className="bg-card/40 border-border/50 backdrop-blur p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:border-primary/50 transition-all"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-lg font-semibold text-foreground">{model.name}</h3>
                  <div className="flex items-center gap-1">
                    <Star className="h-4 w-4 fill-chart-2 text-chart-2" />
                    <span className="text-sm font-medium">{model.rating}</span>
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
                <span className="flex items-center gap-1">
                  <Download className="h-3 w-3" />
                  {model.downloads.toLocaleString()}
                </span>
                <span>Repro: {(model.reproducibility * 100).toFixed(0)}%</span>
              </div>

              <div className="flex gap-2 md:ml-auto">
                <Button asChild variant="outline" size="sm">
                  <Link href={`/models/${model.id}`}>Details</Link>
                </Button>
                <Button asChild size="sm">
                  <Link href={`/models/${model.id}/download`}>Download</Link>
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </main>
  )
}
