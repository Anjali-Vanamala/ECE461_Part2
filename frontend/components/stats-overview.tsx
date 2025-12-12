"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Database, Package, Loader2 } from "lucide-react"
import { fetchArtifacts } from "@/lib/api"

interface Stat {
  label: string
  value: string
  icon: React.ReactNode
  color: string
  loading?: boolean
}

export function StatsOverview() {
  const [stats, setStats] = useState<Stat[]>([
    {
      label: "Total Models",
      value: "0",
      icon: <Database className="h-5 w-5" />,
      color: "text-chart-1",
      loading: true,
    },
    {
      label: "Total Artifacts",
      value: "0",
      icon: <Package className="h-5 w-5" />,
      color: "text-chart-2",
      loading: true,
    },
  ])

  useEffect(() => {
    async function loadStats() {
      try {
        // Fetch all artifacts
        const allArtifacts = await fetchArtifacts()
        const models = allArtifacts.filter((a: any) => a.type === 'model')
        const totalArtifacts = allArtifacts.length

        setStats([
          {
            label: "Total Models",
            value: models.length.toLocaleString(),
            icon: <Database className="h-5 w-5" />,
            color: "text-chart-1",
            loading: false,
          },
          {
            label: "Total Artifacts",
            value: totalArtifacts.toLocaleString(),
            icon: <Package className="h-5 w-5" />,
            color: "text-chart-2",
            loading: false,
          },
        ])
      } catch (error) {
        console.error("Error loading stats:", error)
        // Keep loading state or show error
        setStats(prev => prev.map(stat => ({ ...stat, loading: false, value: "Error" })))
      }
    }

    loadStats()
  }, [])

  return (
    <div className="grid gap-4 md:grid-cols-2 mb-8">
      {stats.map((stat) => (
        <Card key={stat.label} className="bg-card/50 border-border/50 backdrop-blur">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm text-muted-foreground">{stat.label}</h2>
                {stat.loading ? (
                  <div className="flex items-center gap-2 mt-1">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    <span className="text-2xl font-bold text-foreground">Loading...</span>
                  </div>
                ) : (
                  <p className="text-2xl font-bold text-foreground mt-1">{stat.value}</p>
                )}
              </div>
              <div className={`${stat.color} opacity-80`}>{stat.icon}</div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
