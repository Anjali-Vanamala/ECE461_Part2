"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Activity, AlertCircle, CheckCircle, Clock } from "lucide-react"
import { useState } from "react"

interface HealthMetric {
  name: string
  status: "healthy" | "warning" | "critical"
  value: string
  lastChecked: string
}

interface SystemLog {
  timestamp: string
  level: "info" | "warning" | "error"
  message: string
}

export default function HealthPage() {
  const [metrics, setMetrics] = useState<HealthMetric[]>([
    {
      name: "API Server",
      status: "healthy",
      value: "99.98% uptime",
      lastChecked: "2 seconds ago",
    },
    {
      name: "Database",
      status: "healthy",
      value: "245ms avg latency",
      lastChecked: "5 seconds ago",
    },
    {
      name: "Storage",
      status: "healthy",
      value: "15.4 TB used",
      lastChecked: "1 minute ago",
    },
    {
      name: "Cache",
      status: "warning",
      value: "85% capacity",
      lastChecked: "3 seconds ago",
    },
  ])

  const [logs, setLogs] = useState<SystemLog[]>([
    {
      timestamp: "2024-01-15 14:32:15",
      level: "info",
      message: "Model inference completed for BERT-base in 234ms",
    },
    {
      timestamp: "2024-01-15 14:31:42",
      level: "info",
      message: "User download completed: ResNet-50 (440 MB)",
    },
    {
      timestamp: "2024-01-15 14:30:08",
      level: "warning",
      message: "Cache memory at 85% capacity",
    },
    {
      timestamp: "2024-01-15 14:29:15",
      level: "info",
      message: "Model ingestion started: https://huggingface.co/...",
    },
  ])

  const getStatusIcon = (status: HealthMetric["status"]) => {
    if (status === "healthy") {
      return <CheckCircle className="h-5 w-5 text-chart-3" />
    } else if (status === "warning") {
      return <AlertCircle className="h-5 w-5 text-chart-2" />
    }
    return <AlertCircle className="h-5 w-5 text-destructive" />
  }

  const getLevelColor = (level: SystemLog["level"]) => {
    if (level === "info") return "text-chart-1"
    if (level === "warning") return "text-chart-2"
    return "text-destructive"
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">System Health</h1>
            <p className="text-muted-foreground">Real-time monitoring of registry components</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" className="gap-2 bg-transparent">
              <Clock className="h-4 w-4" />
              Last 1 Hour
            </Button>
            <Button size="sm">Run Performance Test</Button>
          </div>
        </div>

        {/* Quick Status */}
        <Card className="mb-8 bg-card/40 border-border/50 backdrop-blur p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-chart-3/20">
              <Activity className="h-6 w-6 text-chart-3" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">System Status</p>
              <p className="text-2xl font-bold text-foreground">All Systems Operational</p>
            </div>
          </div>
        </Card>

        {/* Metrics Grid */}
        <div className="mb-8 grid gap-4 md:grid-cols-2">
          {metrics.map((metric) => (
            <Card key={metric.name} className="bg-card/40 border-border/50 backdrop-blur p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(metric.status)}
                    <h3 className="font-semibold text-foreground">{metric.name}</h3>
                  </div>
                  <p className="mt-2 text-2xl font-bold text-foreground">{metric.value}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Checked {metric.lastChecked}</p>
                </div>
                <Badge variant={metric.status === "healthy" ? "default" : "secondary"} className="ml-2">
                  {metric.status}
                </Badge>
              </div>
            </Card>
          ))}
        </div>

        {/* Logs Section */}
        <Card className="bg-card/40 border-border/50 backdrop-blur">
          <div className="border-b border-border/50 p-6">
            <h2 className="text-xl font-semibold text-foreground">Recent Activity</h2>
          </div>
          <div className="divide-y divide-border/50 max-h-96 overflow-y-auto">
            {logs.map((log, index) => (
              <div key={index} className="flex gap-4 p-4 hover:bg-secondary/5 transition-colors">
                <div className={`text-xs font-bold ${getLevelColor(log.level)}`}>{log.level.toUpperCase()}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-muted-foreground">{log.timestamp}</p>
                  <p className="mt-1 text-sm text-foreground break-words">{log.message}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </main>
  )
}
