"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, Filter } from "lucide-react"

export function SearchModels() {
  const [searchQuery, setSearchQuery] = useState("")

  return (
    <div className="mb-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            id="search-models"
            aria-label="Search models"
            placeholder="Search models by name, task, or description..."
            className="pl-10"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Button variant="outline" className="gap-2 bg-transparent" aria-label="Open filters">
          <Filter className="h-4 w-4" aria-hidden="true" />
          Filters
        </Button>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <div className="text-xs text-muted-foreground">Popular tags:</div>
        {["Vision", "NLP", "Audio", "Fine-tuned", "Production"].map((tag) => (
          <button
            key={tag}
            aria-label={`Filter by ${tag} tag`}
            className="rounded-full bg-secondary/30 px-3 py-1 text-xs text-foreground hover:bg-secondary/50 dark:hover:bg-secondary/70 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  )
}
