"use client"

import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, Grid3x3, List } from "lucide-react"

export type ViewMode = "grid" | "list"

interface SearchModelsProps {
  searchQuery?: string
  onSearchChange?: (query: string) => void
  viewMode?: ViewMode
  onViewModeChange?: (mode: ViewMode) => void
}

export function SearchModels({ 
  searchQuery = "", 
  onSearchChange,
  viewMode = "grid",
  onViewModeChange
}: SearchModelsProps) {
  return (
    <div className="mb-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="search-models"
            aria-label="Search models"
            placeholder="Search models by name, task, or description..."
            className="pl-10"
            value={searchQuery}
            onChange={(e) => onSearchChange?.(e.target.value)}
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant={viewMode === "grid" ? "default" : "outline"}
            size="icon"
            onClick={() => onViewModeChange?.("grid")}
            aria-label="Grid view"
            className="bg-transparent"
          >
            <Grid3x3 className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === "list" ? "default" : "outline"}
            size="icon"
            onClick={() => onViewModeChange?.("list")}
            aria-label="List view"
            className="bg-transparent"
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
