"use client"

import type React from "react"

import { Card } from "@/components/ui/card"
import { Database, TrendingUp, Users, Zap } from "lucide-react"

interface Stat {
  label: string
  value: string
  icon: React.ReactNode
  color: string
}

const stats: Stat[] = [
  {
    label: "Total Models",
    value: "2,847",
    icon: <Database className="h-5 w-5" />,
    color: "text-chart-1",
  },
  {
    label: "Average Rating",
    value: "4.6/5",
    icon: <TrendingUp className="h-5 w-5" />,
    color: "text-chart-2",
  },
  {
    label: "Active Users",
    value: "1,234",
    icon: <Users className="h-5 w-5" />,
    color: "text-chart-3",
  },
  {
    label: "Avg Response Time",
    value: "245ms",
    icon: <Zap className="h-5 w-5" />,
    color: "text-chart-4",
  },
]

export function StatsOverview() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8" role="region" aria-label="Statistics overview">
      {stats.map((stat) => (
        <Card key={stat.label} className="bg-card/50 border-border/50 backdrop-blur">
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm text-muted-foreground">{stat.label}</h2>
                <p className="text-2xl font-bold text-foreground mt-1" aria-label={`${stat.label}: ${stat.value}`}>{stat.value}</p>
              </div>
              <div className={`${stat.color} opacity-80`} aria-hidden="true">{stat.icon}</div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
