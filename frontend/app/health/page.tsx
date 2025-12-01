"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Activity, AlertCircle, CheckCircle, Clock, Loader2 } from "lucide-react"
import { useState, useEffect } from "react"
import { fetchHealth, fetchHealthComponents } from "@/lib/api"

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
  const [healthSummary, setHealthSummary] = useState<any>(null)
  const [healthComponents, setHealthComponents] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [windowMinutes, setWindowMinutes] = useState(60)

  useEffect(() => {
    async function loadHealth() {
      try {
        setLoading(true)
        const [summary, components] = await Promise.all([
          fetchHealth(),
          fetchHealthComponents(windowMinutes, false),
        ])
        setHealthSummary(summary)
        setHealthComponents(components)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load health data")
        console.error("Error loading health:", err)
      } finally {
        setLoading(false)
      }
    }

    loadHealth()
    // Refresh every 30 seconds
    const interval = setInterval(loadHealth, 30000)
    return () => clearInterval(interval)
  }, [windowMinutes])

  // Map backend health data to frontend format
  const metrics: HealthMetric[] = healthComponents?.components?.map((comp: any) => ({
    name: comp.display_name || comp.id,
    status: comp.status === "ok" ? "healthy" : comp.status === "degraded" ? "warning" : "critical",
    value: comp.metrics ? Object.entries(comp.metrics).map(([k, v]) => `${k}: ${v}`).join(", ") : "N/A",
    lastChecked: comp.observed_at ? new Date(comp.observed_at).toLocaleString() : "Unknown",
  })) || []

  const systemStatus = healthSummary?.status === "ok" ? "All Systems Operational" : "System Issues Detected"

  const getStatusIcon = (status: HealthMetric["status"]) => {
    if (status === "healthy") {
      return <CheckCircle className="h-5 w-5 text-chart-3" aria-hidden="true" />
    } else if (status === "warning") {
      return <AlertCircle className="h-5 w-5 text-chart-2" aria-hidden="true" />
    }
    return <AlertCircle className="h-5 w-5 text-destructive" aria-hidden="true" />
  }

  const getLevelColor = (level: SystemLog["level"]) => {
    if (level === "info") return "text-chart-1"
    if (level === "warning") return "text-chart-2"
    return "text-destructive"
  }

  return (
    <main id="main-content" className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">System Health</h1>
            <p className="text-muted-foreground">Real-time monitoring of registry components</p>
          </div>
          <div className="flex gap-3">
            <Button 
              variant="outline" 
              className="gap-2 bg-transparent"
              onClick={() => setWindowMinutes(60)}
              aria-pressed={windowMinutes === 60}
              aria-label="Show last 1 hour"
            >
              <Clock className="h-4 w-4" aria-hidden="true" />
              Last 1 Hour
            </Button>
            <Button size="sm" onClick={() => {
              setWindowMinutes(60)
              setLoading(true)
            }} aria-label="Refresh health data">Refresh</Button>
          </div>
        </header>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12" role="status" aria-live="polite" aria-busy="true">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
            <span className="ml-2 text-muted-foreground">Loading health data...</span>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <Card className="mb-8 bg-destructive/10 border-destructive/30 backdrop-blur p-6" role="alert" aria-live="assertive">
            <p className="text-destructive">Error: {error}</p>
          </Card>
        )}

        {/* Quick Status */}
        {!loading && !error && healthSummary && (
          <section aria-label="System status summary">
            <Card className="mb-8 bg-card/40 border-border/50 backdrop-blur p-6">
            <div className="flex items-center gap-4">
              <div className={`flex h-12 w-12 items-center justify-center rounded-full ${
                healthSummary.status === "ok" ? "bg-chart-3/20" : "bg-destructive/20"
              }`}>
                <Activity className={`h-6 w-6 ${
                  healthSummary.status === "ok" ? "text-chart-3" : "text-destructive"
                }`} aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">System Status</p>
                <p className="text-2xl font-bold text-foreground">{systemStatus}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Checked at: {healthSummary.checked_at ? new Date(healthSummary.checked_at).toLocaleString() : "Unknown"}
                </p>
              </div>
            </div>
          </Card>
          </section>
        )}

        {/* Metrics Grid */}
        {!loading && !error && (
          <section aria-label="Health metrics" className="mb-8 grid gap-4 md:grid-cols-2">
            {metrics.length === 0 ? (
              <Card className="bg-card/40 border-border/50 backdrop-blur p-6 text-center">
                <p className="text-muted-foreground">No health metrics available</p>
              </Card>
            ) : (
              metrics.map((metric) => (
            <Card key={metric.name} className="bg-card/40 border-border/50 backdrop-blur p-6" role="region" aria-label={`${metric.name} health metric`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(metric.status)}
                    <h2 className="font-semibold text-foreground">{metric.name}</h2>
                  </div>
                  <p className="mt-2 text-2xl font-bold text-foreground" aria-label={`${metric.name} value: ${metric.value}`}>{metric.value}</p>
                  <p className="mt-1 text-xs text-muted-foreground" aria-label={`Last checked: ${metric.lastChecked}`}>Checked {metric.lastChecked}</p>
                </div>
                <Badge variant={metric.status === "healthy" ? "default" : "secondary"} className="ml-2" aria-label={`Status: ${metric.status}`}>
                  {metric.status}
                </Badge>
              </div>
            </Card>
              ))
            )}
          </section>
        )}

        {/* Logs Section */}
        {!loading && !error && healthSummary && (
          <section aria-label="System information">
            <Card className="bg-card/40 border-border/50 backdrop-blur">
            <div className="border-b border-border/50 p-6">
              <h2 className="text-xl font-semibold text-foreground">System Information</h2>
            </div>
            <div className="divide-y divide-border/50 max-h-96 overflow-y-auto p-6">
              <div className="space-y-2 text-sm">
                <div>
                  <p className="text-muted-foreground">Version</p>
                  <p className="font-semibold text-foreground">{healthSummary.version || "N/A"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Uptime</p>
                  <p className="font-semibold text-foreground">
                    {healthSummary.uptime_seconds ? `${Math.floor(healthSummary.uptime_seconds / 3600)}h ${Math.floor((healthSummary.uptime_seconds % 3600) / 60)}m` : "N/A"}
                  </p>
                </div>
                {healthSummary.request_summary && (
                  <>
                    <div>
                      <p className="text-muted-foreground">Total Requests</p>
                      <p className="font-semibold text-foreground">{healthSummary.request_summary.total_requests || 0}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Unique Clients</p>
                      <p className="font-semibold text-foreground">{healthSummary.request_summary.unique_clients || 0}</p>
                    </div>
                  </>
                )}
              </div>
            </div>
          </Card>
          </section>
        )}
      </div>
    </main>
  )
}

