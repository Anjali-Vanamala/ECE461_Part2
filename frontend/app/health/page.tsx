"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  Activity, 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  Loader2, 
  RefreshCw,
  Server,
  Users,
  TrendingUp,
  Globe,
  Database,
  Code,
  FileText,
  BarChart3
} from "lucide-react"
import { useState, useEffect } from "react"
import { fetchHealth, fetchHealthComponents } from "@/lib/api"
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend } from "@/components/ui/chart"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, BarChart, Bar } from "recharts"

export default function HealthPage() {
  const [healthSummary, setHealthSummary] = useState<any>(null)
  const [healthComponents, setHealthComponents] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [windowMinutes, setWindowMinutes] = useState(60)
  const [includeTimeline, setIncludeTimeline] = useState(true)
  const [isDarkMode, setIsDarkMode] = useState(false)

  // Detect dark mode
  useEffect(() => {
    const checkDarkMode = () => {
      setIsDarkMode(document.documentElement.classList.contains('dark'))
    }
    checkDarkMode()
    const observer = new MutationObserver(checkDarkMode)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    })
    return () => observer.disconnect()
  }, [])

    async function loadHealth() {
      try {
        setLoading(true)
        const [summary, components] = await Promise.all([
          fetchHealth(),
        fetchHealthComponents(windowMinutes, includeTimeline),
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

  useEffect(() => {
    loadHealth()
    // Refresh every 30 seconds
    const interval = setInterval(loadHealth, 30000)
    return () => clearInterval(interval)
  }, [windowMinutes, includeTimeline])

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "ok":
        return "bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30"
      case "degraded":
        return "bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border-yellow-500/30"
      case "critical":
        return "bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30"
      default:
        return "bg-gray-500/20 text-gray-600 dark:text-gray-400 border-gray-500/30"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "ok":
        return <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
      case "degraded":
        return <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
      case "critical":
        return <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
      default:
        return <AlertCircle className="h-5 w-5 text-gray-600 dark:text-gray-400" />
    }
  }

  // Prepare timeline data for chart
  const timelineData = healthComponents?.components?.[0]?.timeline?.map((entry: any) => ({
    time: new Date(entry.bucket).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    requests: entry.value,
    fullTime: new Date(entry.bucket).toLocaleString()
  })) || []

  const chartConfig = {
    requests: {
      label: "Requests",
      color: "hsl(var(--chart-1))",
    },
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">System Health Dashboard</h1>
            <p className="text-muted-foreground">Real-time monitoring and metrics for the Model Registry API</p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <Button 
              variant={windowMinutes === 60 ? "default" : "outline"}
              size="sm"
              onClick={() => setWindowMinutes(60)}
            >
              <Clock className="h-4 w-4 mr-2" />
              1 Hour
            </Button>
            <Button 
              variant={windowMinutes === 30 ? "default" : "outline"}
              size="sm"
              onClick={() => setWindowMinutes(30)}
            >
              30 Min
            </Button>
            <Button 
              variant={windowMinutes === 15 ? "default" : "outline"}
              size="sm"
              onClick={() => setWindowMinutes(15)}
            >
              15 Min
            </Button>
            <Button 
              variant="outline"
              size="sm"
              onClick={loadHealth}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading health data...</span>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <Card className="mb-8 bg-destructive/10 border-destructive/30 p-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <p className="text-destructive font-medium">Error: {error}</p>
            </div>
          </Card>
        )}

        {!loading && !error && healthSummary && healthComponents && (
          <>
            {/* System Status Card */}
            <Card className="mb-6 bg-gradient-to-br from-card/50 to-card/30 border-border/50 p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={`flex h-16 w-16 items-center justify-center rounded-full ${
                    healthSummary.status === "ok" 
                      ? "bg-green-500/20" 
                      : healthSummary.status === "degraded"
                      ? "bg-yellow-500/20"
                      : "bg-red-500/20"
                  }`}>
                    {getStatusIcon(healthSummary.status)}
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Overall System Status</p>
                    <p className="text-3xl font-bold text-foreground capitalize">
                      {healthSummary.status === "ok" ? "All Systems Operational" : 
                       healthSummary.status === "degraded" ? "System Degraded" : 
                       "System Critical"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Last checked: {formatDate(healthSummary.checked_at)}
                    </p>
                  </div>
                </div>
                <Badge 
                  variant="outline" 
                  className={`${getStatusColor(healthSummary.status)} text-sm px-4 py-2`}
                >
                  {healthSummary.status.toUpperCase()}
                </Badge>
              </div>
            </Card>

            {/* Key Metrics Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
              {/* Uptime */}
              <Card className="bg-card/50 border-border/50 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Uptime</p>
                    <p className="text-2xl font-bold text-foreground">
                      {healthSummary.uptime_seconds 
                        ? formatUptime(healthSummary.uptime_seconds)
                        : "N/A"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {healthComponents?.components?.[0]?.metrics?.uptime_hours 
                        ? `${healthComponents.components[0].metrics.uptime_hours.toFixed(2)} hours`
                        : ""}
                    </p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <Server className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                </div>
              </Card>

              {/* Requests Per Minute */}
              <Card className="bg-card/50 border-border/50 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Requests/Min</p>
                    <p className="text-2xl font-bold text-foreground">
                      {healthComponents?.components?.[0]?.metrics?.requests_per_minute 
                        ? healthComponents.components[0].metrics.requests_per_minute.toFixed(2)
                        : "0.00"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Last {windowMinutes} minutes
                    </p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <TrendingUp className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                  </div>
                </div>
              </Card>

              {/* Total Requests */}
              <Card className="bg-card/50 border-border/50 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Total Requests</p>
                    <p className="text-2xl font-bold text-foreground">
                      {healthSummary.request_summary?.total_requests || 0}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      In observation window
                    </p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-green-500/20 flex items-center justify-center">
                    <Activity className="h-6 w-6 text-green-600 dark:text-green-400" />
                  </div>
                </div>
              </Card>

              {/* Unique Clients */}
              <Card className="bg-card/50 border-border/50 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Unique Clients</p>
                    <p className="text-2xl font-bold text-foreground">
                      {healthSummary.request_summary?.unique_clients || 0}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Distinct IP addresses
                    </p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-orange-500/20 flex items-center justify-center">
                    <Users className="h-6 w-6 text-orange-600 dark:text-orange-400" />
                  </div>
                </div>
              </Card>
            </div>

            <div className="grid gap-6 md:grid-cols-2 mb-6">
              {/* Requests by Route */}
              <Card className="bg-card/50 border-border/50">
                <div className="border-b border-border/50 p-6">
                  <div className="flex items-center gap-2">
                    <Globe className="h-5 w-5 text-muted-foreground" />
                    <h2 className="text-xl font-semibold text-foreground">Requests by Route</h2>
                  </div>
                </div>
                <div className="p-6">
                  {healthSummary.request_summary?.per_route && 
                   Object.keys(healthSummary.request_summary.per_route).length > 0 ? (
                    <div className="space-y-3">
                      {Object.entries(healthSummary.request_summary.per_route)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .map(([route, count]) => (
                        <div key={route} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                          <div className="flex items-center gap-3">
                            <div className="h-2 w-2 rounded-full bg-chart-1"></div>
                            <code className="text-sm font-mono text-foreground">{route || "/"}</code>
                          </div>
                          <Badge variant="secondary" className="font-mono">
                            {count as number}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-4">No route data available</p>
            )}
          </div>
              </Card>

              {/* Requests by Artifact Type */}
              <Card className="bg-card/50 border-border/50">
            <div className="border-b border-border/50 p-6">
                  <div className="flex items-center gap-2">
                    <Database className="h-5 w-5 text-muted-foreground" />
                    <h2 className="text-xl font-semibold text-foreground">Requests by Artifact Type</h2>
                  </div>
                </div>
                <div className="p-6">
                  {healthSummary.request_summary?.per_artifact_type && 
                   Object.keys(healthSummary.request_summary.per_artifact_type).length > 0 ? (
                    <div className="space-y-3">
                      {Object.entries(healthSummary.request_summary.per_artifact_type)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .map(([type, count]) => {
                          const icons: Record<string, any> = {
                            model: <Database className="h-4 w-4" />,
                            dataset: <FileText className="h-4 w-4" />,
                            code: <Code className="h-4 w-4" />,
                          }
                          return (
                            <div key={type} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                              <div className="flex items-center gap-3">
                                {icons[type] || <Database className="h-4 w-4" />}
                                <span className="text-sm font-medium text-foreground capitalize">{type}</span>
                              </div>
                              <Badge variant="secondary" className="font-mono">
                                {count as number}
                              </Badge>
                            </div>
                          )
                        })}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-center py-4">No artifact type data available</p>
                  )}
                </div>
              </Card>
            </div>

            {/* Timeline Chart */}
            {includeTimeline && timelineData.length > 0 && (
              <Card className="mb-6 bg-card/50 border-border/50">
                <div className="border-b border-border/50 p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5 text-muted-foreground" />
                      <h2 className="text-xl font-semibold text-foreground">Request Timeline</h2>
                    </div>
                    <Badge variant="outline">Last {windowMinutes} minutes</Badge>
                  </div>
                </div>
                <div className="p-6">
                  <ChartContainer config={chartConfig} className="h-[300px]">
                    <LineChart data={timelineData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis 
                        dataKey="time" 
                        className="text-xs"
                        tick={{ fill: 'currentColor' }}
                      />
                      <YAxis 
                        className="text-xs"
                        tick={{ fill: 'currentColor' }}
                      />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Line 
                        type="monotone" 
                        dataKey="requests" 
                        stroke="hsl(var(--chart-1))"
                        strokeWidth={2}
                        dot={{ r: 4, fill: isDarkMode ? "#ffffff" : "#000000", stroke: "hsl(var(--chart-1))", strokeWidth: 2 }}
                        activeDot={{ r: 6, fill: isDarkMode ? "#ffffff" : "#000000", stroke: "hsl(var(--chart-1))", strokeWidth: 2 }}
                      />
                    </LineChart>
                  </ChartContainer>
                </div>
              </Card>
            )}

            {/* Component Details */}
            {healthComponents?.components?.map((component: any) => (
              <Card key={component.id} className="mb-6 bg-card/50 border-border/50">
                <div className="border-b border-border/50 p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(component.status)}
                <div>
                        <h2 className="text-xl font-semibold text-foreground">{component.display_name}</h2>
                        <p className="text-sm text-muted-foreground">{component.description}</p>
                      </div>
                    </div>
                    <Badge 
                      variant="outline" 
                      className={`${getStatusColor(component.status)} text-sm px-4 py-2`}
                    >
                      {component.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>
                <div className="p-6">
                  <div className="grid gap-6 md:grid-cols-2">
                    {/* Metrics */}
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-4">Metrics</h3>
                      <div className="space-y-3">
                        {component.metrics && Object.entries(component.metrics).map(([key, value]) => (
                          <div key={key} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                            <span className="text-sm text-muted-foreground capitalize">
                              {key.replace(/_/g, ' ')}
                            </span>
                            <span className="text-sm font-mono font-semibold text-foreground">
                              {typeof value === 'number' 
                                ? value.toFixed(2) 
                                : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* System Info */}
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-4">System Information</h3>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                          <span className="text-sm text-muted-foreground">Version</span>
                          <span className="text-sm font-mono font-semibold text-foreground">
                            {healthSummary.version || "N/A"}
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                          <span className="text-sm text-muted-foreground">Observed At</span>
                          <span className="text-sm font-mono font-semibold text-foreground">
                            {formatDate(component.observed_at)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                          <span className="text-sm text-muted-foreground">Window</span>
                          <span className="text-sm font-mono font-semibold text-foreground">
                            {healthComponents.window_minutes} minutes
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                          <span className="text-sm text-muted-foreground">Window Start</span>
                          <span className="text-sm font-mono font-semibold text-foreground">
                            {formatDate(healthSummary.request_summary?.window_start)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                          <span className="text-sm text-muted-foreground">Window End</span>
                          <span className="text-sm font-mono font-semibold text-foreground">
                            {formatDate(healthSummary.request_summary?.window_end)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Issues */}
                  {component.issues && component.issues.length > 0 && (
                    <div className="mt-6">
                      <h3 className="text-sm font-semibold text-foreground mb-4">Issues</h3>
                      <div className="space-y-2">
                        {component.issues.map((issue: any, idx: number) => (
                          <div 
                            key={idx} 
                            className={`p-3 rounded-lg border ${
                              issue.severity === 'error' 
                                ? 'bg-red-500/10 border-red-500/30' 
                                : issue.severity === 'warning'
                                ? 'bg-yellow-500/10 border-yellow-500/30'
                                : 'bg-blue-500/10 border-blue-500/30'
                            }`}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="outline" className="text-xs">
                                {issue.severity}
                              </Badge>
                              <span className="text-sm font-medium text-foreground">{issue.summary}</span>
                            </div>
                            {issue.details && (
                              <p className="text-xs text-muted-foreground mt-1">{issue.details}</p>
                )}
              </div>
                        ))}
                      </div>
                    </div>
                  )}
            </div>
          </Card>
            ))}
          </>
        )}
      </div>
    </main>
  )
}
