"use client"

import { Card } from "@/components/ui/card"
import { GitBranch } from "lucide-react"

interface LineageGraphProps {
  lineage: string[]
}

export function LineageGraph({ lineage }: LineageGraphProps) {
  return (
    <div className="space-y-3">
      {lineage.map((parent, index) => (
        <div key={index} className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/20">
            <GitBranch className="h-4 w-4 text-primary" />
          </div>
          <div className="flex-1">
            <Card className="bg-secondary/20 border-border/50 p-3">
              <p className="text-sm font-medium text-foreground">{parent}</p>
            </Card>
          </div>
          {index < lineage.length - 1 && <div className="w-0.5 h-8 bg-border/50 ml-4" />}
        </div>
      ))}
    </div>
  )
}
