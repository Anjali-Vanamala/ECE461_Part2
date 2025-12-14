"use client"

import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
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
import { useState, useEffect, useRef } from "react"
import { fetchHealth, fetchHealthComponents, startDownloadBenchmark, getDownloadBenchmarkStatus, BACKEND_ENDPOINTS, BackendType } from "@/lib/api"
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
  
  // Download benchmark state
  const [downloadBenchmarkRunning, setDownloadBenchmarkRunning] = useState(false)
  const [downloadBenchmarkResults, setDownloadBenchmarkResults] = useState<any>(null)
  const [downloadBenchmarkProgress, setDownloadBenchmarkProgress] = useState<string | null>(null)
  const [downloadBenchmarkCurrentProgress, setDownloadBenchmarkCurrentProgress] = useState<string | null>(null) // X/100 format
  const [downloadBenchmarkError, setDownloadBenchmarkError] = useState<string | null>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Backend selection state for benchmarking
  const [selectedBackend, setSelectedBackend] = useState<BackendType>('ecs')
  const [benchmarkResultsByBackend, setBenchmarkResultsByBackend] = useState<Record<BackendType, any>>({
    ecs: null,
    lambda: null,
  })

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
  
  // Load saved download benchmark results from localStorage and resume polling if needed
  useEffect(() => {
    // Load per-backend results
    const savedEcsResults = localStorage.getItem('downloadBenchmarkResults_ecs')
    const savedLambdaResults = localStorage.getItem('downloadBenchmarkResults_lambda')

    const loadedResults: Record<BackendType, any> = { ecs: null, lambda: null }

    if (savedEcsResults) {
      try {
        loadedResults.ecs = JSON.parse(savedEcsResults)
      } catch (e) {
        console.error('Failed to parse saved ECS benchmark results:', e)
      }
    }

    if (savedLambdaResults) {
      try {
        loadedResults.lambda = JSON.parse(savedLambdaResults)
      } catch (e) {
        console.error('Failed to parse saved Lambda benchmark results:', e)
      }
    }

    setBenchmarkResultsByBackend(loadedResults)

    // Also load the legacy single result for backward compatibility
    const savedResults = localStorage.getItem('downloadBenchmarkResults')
    if (savedResults) {
      try {
        const parsed = JSON.parse(savedResults)
        setDownloadBenchmarkResults(parsed)
        console.log('Loaded saved download benchmark results from localStorage')
      } catch (e) {
        console.error('Failed to parse saved download benchmark results:', e)
      }
    }
    
    // Check if there's a running benchmark to resume
    const savedJobId = localStorage.getItem('downloadBenchmarkJobId')
    const savedRunning = localStorage.getItem('downloadBenchmarkRunning')
    const savedBackend = localStorage.getItem('downloadBenchmarkBackend') as BackendType | null
    
    if (savedJobId && savedRunning === 'true') {
      // Restore selected backend if available
      if (savedBackend && (savedBackend === 'ecs' || savedBackend === 'lambda')) {
        setSelectedBackend(savedBackend)
      }
      
      console.log('Resuming polling for benchmark job:', savedJobId, 'on backend:', savedBackend || 'unknown')
      setDownloadBenchmarkRunning(true)
      
      // Get the backend URL for polling
      const backendUrl = savedBackend && (savedBackend === 'ecs' || savedBackend === 'lambda')
        ? BACKEND_ENDPOINTS[savedBackend].url
        : undefined
      
      // Resume polling
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await getDownloadBenchmarkStatus(savedJobId, backendUrl)
          
          if (statusResponse.progress) {
            setDownloadBenchmarkProgress(statusResponse.progress)
          }
          if (statusResponse.current_progress) {
            setDownloadBenchmarkCurrentProgress(statusResponse.current_progress)
          }
          
          if (statusResponse.status === 'completed') {
            const completedBackend = savedBackend || 'ecs' // Default to ecs if not saved
            console.log(`Download benchmark completed on ${completedBackend}! Results:`, statusResponse.results)
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            setDownloadBenchmarkResults(statusResponse.results)
            setDownloadBenchmarkRunning(false)
            setDownloadBenchmarkProgress(null)
            setDownloadBenchmarkCurrentProgress(null)
            // Save per-backend results
            if (completedBackend === 'ecs' || completedBackend === 'lambda') {
              localStorage.setItem(`downloadBenchmarkResults_${completedBackend}`, JSON.stringify(statusResponse.results))
              localStorage.setItem(`downloadBenchmarkCompletedAt_${completedBackend}`, new Date().toISOString())
              setBenchmarkResultsByBackend(prev => ({
                ...prev,
                [completedBackend]: statusResponse.results
              }))
            }
            // Also save to legacy key for backward compat
            localStorage.setItem('downloadBenchmarkResults', JSON.stringify(statusResponse.results))
            localStorage.setItem('downloadBenchmarkCompletedAt', new Date().toISOString())
            localStorage.removeItem('downloadBenchmarkJobId')
            localStorage.removeItem('downloadBenchmarkRunning')
            localStorage.removeItem('downloadBenchmarkBackend')
          } else if (statusResponse.status === 'failed') {
            console.error('Download benchmark failed:', statusResponse.error)
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            setDownloadBenchmarkError(statusResponse.error || 'Download benchmark failed')
            setDownloadBenchmarkRunning(false)
            setDownloadBenchmarkProgress(null)
            setDownloadBenchmarkCurrentProgress(null)
            localStorage.removeItem('downloadBenchmarkJobId')
            localStorage.removeItem('downloadBenchmarkRunning')
            localStorage.removeItem('downloadBenchmarkBackend')
          }
        } catch (err) {
          console.error('Error checking download benchmark status:', err)
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
          setDownloadBenchmarkError(err instanceof Error ? err.message : "Failed to check benchmark status")
          setDownloadBenchmarkRunning(false)
          localStorage.removeItem('downloadBenchmarkJobId')
          localStorage.removeItem('downloadBenchmarkRunning')
          localStorage.removeItem('downloadBenchmarkBackend')
        }
      }, 2000)
      
      pollIntervalRef.current = pollInterval
      
      // Cleanup on unmount
      return () => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
      }
    }
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

  // Helper function to safely calculate percentage difference
  const calculatePercentageDifference = (
    ecsValue: number | undefined,
    lambdaValue: number | undefined,
    isLowerBetter: boolean = false
  ): { percentage: string; isBetter: boolean; faster: string } | null => {
    if (!ecsValue || !lambdaValue || ecsValue === 0 || lambdaValue === 0) {
      return null
    }
    
    const diff = ((lambdaValue / ecsValue - 1) * 100)
    const isBetter = isLowerBetter 
      ? ecsValue < lambdaValue 
      : ecsValue > lambdaValue
    const faster = isBetter ? 'ECS' : 'Lambda'
    
    return {
      percentage: diff.toFixed(1),
      isBetter,
      faster
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

            {/* Download Benchmark Section */}
            <Card className="mb-6 bg-card/50 border-border/50">
              <div className="border-b border-border/50 p-6">
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <BarChart3 className="h-6 w-6 text-chart-1" />
                      <div>
                        <h2 className="text-xl font-semibold text-foreground">Download Performance Benchmark</h2>
                        <p className="text-sm text-muted-foreground">
                          Compare ECS vs Lambda performance with 100 concurrent downloads
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Backend Selector */}
                  <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between p-4 rounded-lg bg-muted/30">
                    <div className="flex flex-col gap-2">
                      <p className="text-sm font-medium text-foreground">Select Compute Backend</p>
                      <div className="flex gap-2">
                        {(Object.keys(BACKEND_ENDPOINTS) as BackendType[]).map((backendKey) => {
                          const backend = BACKEND_ENDPOINTS[backendKey]
                          return (
                            <Tooltip key={backendKey}>
                              <TooltipTrigger asChild>
                                <span>
                            <Button
                              variant={selectedBackend === backendKey ? "default" : "outline"}
                              size="sm"
                              onClick={() => setSelectedBackend(backendKey)}
                              disabled={downloadBenchmarkRunning}
                              className="gap-2"
                            >
                              <Server className="h-4 w-4" />
                              {backend.name}
                            </Button>
                                </span>
                              </TooltipTrigger>
                              {downloadBenchmarkRunning && (
                                <TooltipContent>
                                  <p>Cannot change backend while benchmark is running</p>
                                </TooltipContent>
                              )}
                            </Tooltip>
                          )
                        })}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">
                        {BACKEND_ENDPOINTS[selectedBackend].description}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Cold Start: {BACKEND_ENDPOINTS[selectedBackend].coldStart}
                      </p>
                    </div>
                  </div>

                  {/* Run Benchmark Button */}
                  <div className="flex justify-end">
                    <Button
                      onClick={async () => {
                        const backendUrl = BACKEND_ENDPOINTS[selectedBackend].url
                        try {
                          setDownloadBenchmarkRunning(true)
                          setDownloadBenchmarkResults(null)
                          setDownloadBenchmarkError(null)
                          setDownloadBenchmarkProgress(null)
                          setDownloadBenchmarkCurrentProgress(null)

                          const startResponse = await startDownloadBenchmark(backendUrl)
                          const jobId = startResponse.job_id
                          console.log(`Download benchmark started on ${selectedBackend} with job ID:`, jobId)
                        
                          // Store jobId, running state, and selected backend in localStorage
                          localStorage.setItem('downloadBenchmarkJobId', jobId)
                          localStorage.setItem('downloadBenchmarkRunning', 'true')
                          localStorage.setItem('downloadBenchmarkBackend', selectedBackend)

                          // Clear any existing interval
                          if (pollIntervalRef.current) {
                            clearInterval(pollIntervalRef.current)
                          }

                          // Poll for results every 2 seconds
                          const pollInterval = setInterval(async () => {
                            try {
                              const statusResponse = await getDownloadBenchmarkStatus(jobId, backendUrl)
                            
                            if (statusResponse.progress) {
                              setDownloadBenchmarkProgress(statusResponse.progress)
                            }
                            if (statusResponse.current_progress) {
                              setDownloadBenchmarkCurrentProgress(statusResponse.current_progress)
                            }
                            
                              if (statusResponse.status === 'completed') {
                                console.log(`Download benchmark completed on ${selectedBackend}! Results:`, statusResponse.results)
                                clearInterval(pollInterval)
                                pollIntervalRef.current = null
                                setDownloadBenchmarkResults(statusResponse.results)
                                setDownloadBenchmarkRunning(false)
                                setDownloadBenchmarkProgress(null)
                                setDownloadBenchmarkCurrentProgress(null)
                                // Save per-backend results
                                localStorage.setItem(`downloadBenchmarkResults_${selectedBackend}`, JSON.stringify(statusResponse.results))
                                localStorage.setItem(`downloadBenchmarkCompletedAt_${selectedBackend}`, new Date().toISOString())
                                // Also save to legacy key for backward compat
                                localStorage.setItem('downloadBenchmarkResults', JSON.stringify(statusResponse.results))
                                localStorage.setItem('downloadBenchmarkCompletedAt', new Date().toISOString())
                                localStorage.removeItem('downloadBenchmarkJobId')
                                localStorage.removeItem('downloadBenchmarkRunning')
                                localStorage.removeItem('downloadBenchmarkBackend')
                                // Update per-backend state
                                setBenchmarkResultsByBackend(prev => ({
                                  ...prev,
                                  [selectedBackend]: statusResponse.results
                                }))
                              } else if (statusResponse.status === 'failed') {
                                console.error('Download benchmark failed:', statusResponse.error)
                                clearInterval(pollInterval)
                                pollIntervalRef.current = null
                                setDownloadBenchmarkError(statusResponse.error || 'Download benchmark failed')
                                setDownloadBenchmarkRunning(false)
                                setDownloadBenchmarkProgress(null)
                                setDownloadBenchmarkCurrentProgress(null)
                                localStorage.removeItem('downloadBenchmarkJobId')
                                localStorage.removeItem('downloadBenchmarkRunning')
                                localStorage.removeItem('downloadBenchmarkBackend')
                              }
                            } catch (err) {
                              console.error('Error checking download benchmark status:', err)
                              clearInterval(pollInterval)
                              pollIntervalRef.current = null
                              setDownloadBenchmarkError(err instanceof Error ? err.message : "Failed to check benchmark status")
                              setDownloadBenchmarkRunning(false)
                              localStorage.removeItem('downloadBenchmarkJobId')
                              localStorage.removeItem('downloadBenchmarkRunning')
                              localStorage.removeItem('downloadBenchmarkBackend')
                            }
                          }, 2000)
                        
                        pollIntervalRef.current = pollInterval
                        
                          // Cleanup after 15 minutes (safety timeout)
                          setTimeout(() => {
                            if (pollIntervalRef.current) {
                              clearInterval(pollIntervalRef.current)
                              pollIntervalRef.current = null
                            }
                            if (downloadBenchmarkRunning) {
                              setDownloadBenchmarkError("Benchmark timeout - check status manually")
                              setDownloadBenchmarkRunning(false)
                              localStorage.removeItem('downloadBenchmarkJobId')
                              localStorage.removeItem('downloadBenchmarkRunning')
                              localStorage.removeItem('downloadBenchmarkBackend')
                            }
                          }, 900000)
                        } catch (err) {
                          setDownloadBenchmarkError(err instanceof Error ? err.message : "Failed to start download benchmark")
                          console.error("Error starting download benchmark:", err)
                          setDownloadBenchmarkRunning(false)
                          localStorage.removeItem('downloadBenchmarkJobId')
                          localStorage.removeItem('downloadBenchmarkRunning')
                          localStorage.removeItem('downloadBenchmarkBackend')
                        }
                      }}
                    disabled={downloadBenchmarkRunning}
                    className="gap-2"
                  >
                    {downloadBenchmarkRunning ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Activity className="h-4 w-4" />
                        Run Benchmark
                      </>
                    )}
                  </Button>
                  </div>
                </div>
              </div>

              <div className="p-6">
                {downloadBenchmarkRunning && (
                  <div className="mb-6">
                    <div className="flex items-center justify-center gap-3 p-6">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      <div className="flex flex-col gap-1">
                        <p className="text-muted-foreground">Executing download benchmark... This may take 3-5 minutes.</p>
                        {downloadBenchmarkCurrentProgress && (
                          <p className="text-lg font-semibold text-foreground">
                            {downloadBenchmarkCurrentProgress} downloads completed
                          </p>
                        )}
                        {downloadBenchmarkProgress && (
                          <p className="text-xs text-muted-foreground/70 italic">{downloadBenchmarkProgress}</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                
                {downloadBenchmarkError && (
                  <Card className="mb-6 bg-destructive/10 border-destructive/30 backdrop-blur p-6">
                    <div className="flex gap-3">
                      <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-foreground mb-1">Benchmark Failed</p>
                        <p className="text-sm text-muted-foreground">{downloadBenchmarkError}</p>
                      </div>
                    </div>
                  </Card>
                )}
                
                {downloadBenchmarkResults && !downloadBenchmarkRunning && (
                  <>
                    {localStorage.getItem('downloadBenchmarkCompletedAt') && (
                      <p className="text-xs text-muted-foreground/70 mb-4">
                        Last completed: {new Date(localStorage.getItem('downloadBenchmarkCompletedAt') || '').toLocaleString()}
                      </p>
                    )}
                    
                    {/* Test Configuration */}
                    <div className="mb-6">
                      <h3 className="text-sm font-semibold text-foreground mb-4">Test Configuration</h3>
                      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                        <div className="p-3 rounded-lg bg-muted/30">
                          <p className="text-xs text-muted-foreground">API Base URL</p>
                          <p className="text-sm font-mono font-semibold text-foreground break-all">
                            {downloadBenchmarkResults.test_configuration?.api_base_url || 'N/A'}
                          </p>
                        </div>
                        <div className="p-3 rounded-lg bg-muted/30">
                          <p className="text-xs text-muted-foreground">Concurrent Requests</p>
                          <p className="text-sm font-mono font-semibold text-foreground">
                            {downloadBenchmarkResults.test_configuration?.concurrent_requests || 'N/A'}
                          </p>
                        </div>
                        <div className="p-3 rounded-lg bg-muted/30">
                          <p className="text-xs text-muted-foreground">Test Timestamp</p>
                          <p className="text-sm font-mono font-semibold text-foreground">
                            {downloadBenchmarkResults.test_configuration?.test_timestamp 
                              ? new Date(downloadBenchmarkResults.test_configuration.test_timestamp).toLocaleString()
                              : 'N/A'}
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Black-Box Metrics */}
                    <div className="mb-6">
                      <h3 className="text-sm font-semibold text-foreground mb-4">Black-Box Metrics (Performance)</h3>
                      
                      {/* Throughput */}
                      <div className="mb-4">
                        <h4 className="text-xs font-medium text-muted-foreground mb-2">Throughput</h4>
                        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Requests/Second</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.throughput?.requests_per_second?.toFixed(2) || 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Throughput (Mbps)</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.throughput?.mbps?.toFixed(2) || 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Total Downloaded</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.throughput?.total_downloaded_mb?.toFixed(2) || 'N/A'} MB
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Avg File Size</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.throughput?.average_file_size_kb?.toFixed(2) || 'N/A'} KB
                            </p>
                          </div>
                        </div>
                      </div>
                      
                      {/* Latency */}
                      <div className="mb-4">
                        <h4 className="text-xs font-medium text-muted-foreground mb-2">Latency (ms)</h4>
                        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Mean</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.latency?.mean_ms?.toFixed(2) || 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Median</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.latency?.median_ms?.toFixed(2) || 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">P99</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.latency?.p99_ms?.toFixed(2) || 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Min</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.latency?.min_ms?.toFixed(2) || 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Max</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.latency?.max_ms?.toFixed(2) || 'N/A'}
                            </p>
                          </div>
                        </div>
                      </div>
                      
                      {/* Request Summary */}
                      <div>
                        <h4 className="text-xs font-medium text-muted-foreground mb-2">Request Summary</h4>
                        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Total Requests</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.request_summary?.total_requests || 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Successful</p>
                            <p className="text-lg font-mono font-semibold text-chart-3">
                              {downloadBenchmarkResults.black_box_metrics?.request_summary?.successful || 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Failed</p>
                            <p className="text-lg font-mono font-semibold text-destructive">
                              {downloadBenchmarkResults.black_box_metrics?.request_summary?.failed ?? 'N/A'}
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Success Rate</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.request_summary?.success_rate?.toFixed(2) || 'N/A'}%
                            </p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/30">
                            <p className="text-xs text-muted-foreground">Total Duration</p>
                            <p className="text-lg font-mono font-semibold text-foreground">
                              {downloadBenchmarkResults.black_box_metrics?.request_summary?.total_duration_seconds?.toFixed(2) || 'N/A'}s
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </>
                )}

                {/* ECS vs Lambda Comparison */}
                {(benchmarkResultsByBackend.ecs || benchmarkResultsByBackend.lambda) && (
                  <div className="mt-8 pt-6 border-t border-border/50">
                    <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                      <TrendingUp className="h-5 w-5" />
                      ECS vs Lambda Comparison
                    </h3>

                    {/* Show message if only one backend has results */}
                    {(!benchmarkResultsByBackend.ecs || !benchmarkResultsByBackend.lambda) && (
                      <div className="mb-4 p-3 rounded-lg bg-muted/30 text-sm text-muted-foreground">
                        Run benchmarks on both ECS and Lambda to see a side-by-side comparison.
                        {benchmarkResultsByBackend.ecs && " (ECS results available)"}
                        {benchmarkResultsByBackend.lambda && " (Lambda results available)"}
                      </div>
                    )}

                    {/* Comparison Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-border/50">
                            <th className="text-left p-3 font-medium text-muted-foreground">Metric</th>
                            <th className="text-right p-3 font-medium text-muted-foreground">
                              <div className="flex items-center justify-end gap-2">
                                <Server className="h-4 w-4" />
                                ECS (Fargate)
                              </div>
                            </th>
                            <th className="text-right p-3 font-medium text-muted-foreground">
                              <div className="flex items-center justify-end gap-2">
                                <Server className="h-4 w-4" />
                                Lambda
                              </div>
                            </th>
                            <th className="text-right p-3 font-medium text-muted-foreground">Difference</th>
                          </tr>
                        </thead>
                        <tbody>
                          {/* Throughput RPS */}
                          <tr className="border-b border-border/30">
                            <td className="p-3 text-foreground">Throughput (req/s)</td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.ecs?.black_box_metrics?.throughput?.requests_per_second?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.lambda?.black_box_metrics?.throughput?.requests_per_second?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {(() => {
                                const ecsValue = benchmarkResultsByBackend.ecs?.black_box_metrics?.throughput?.requests_per_second
                                const lambdaValue = benchmarkResultsByBackend.lambda?.black_box_metrics?.throughput?.requests_per_second
                                const diff = calculatePercentageDifference(ecsValue, lambdaValue, false)
                                if (!diff) return '-'
                                return (
                                  <span className={diff.isBetter ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                                    {diff.percentage}% ({diff.faster} faster)
                                </span>
                                )
                              })()}
                            </td>
                          </tr>
                          {/* Mean Latency */}
                          <tr className="border-b border-border/30">
                            <td className="p-3 text-foreground">Mean Latency (ms)</td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.ecs?.black_box_metrics?.latency?.mean_ms?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.lambda?.black_box_metrics?.latency?.mean_ms?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {(() => {
                                const ecsValue = benchmarkResultsByBackend.ecs?.black_box_metrics?.latency?.mean_ms
                                const lambdaValue = benchmarkResultsByBackend.lambda?.black_box_metrics?.latency?.mean_ms
                                const diff = calculatePercentageDifference(ecsValue, lambdaValue, true)
                                if (!diff) return '-'
                                return (
                                  <span className={diff.isBetter ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                                    {diff.percentage}% ({diff.faster} faster)
                                </span>
                                )
                              })()}
                            </td>
                          </tr>
                          {/* Median Latency */}
                          <tr className="border-b border-border/30">
                            <td className="p-3 text-foreground">Median Latency (ms)</td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.ecs?.black_box_metrics?.latency?.median_ms?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.lambda?.black_box_metrics?.latency?.median_ms?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {(() => {
                                const ecsValue = benchmarkResultsByBackend.ecs?.black_box_metrics?.latency?.median_ms
                                const lambdaValue = benchmarkResultsByBackend.lambda?.black_box_metrics?.latency?.median_ms
                                const diff = calculatePercentageDifference(ecsValue, lambdaValue, true)
                                if (!diff) return '-'
                                return (
                                  <span className={diff.isBetter ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                                    {diff.percentage}% ({diff.faster} faster)
                                </span>
                                )
                              })()}
                            </td>
                          </tr>
                          {/* P99 Latency */}
                          <tr className="border-b border-border/30">
                            <td className="p-3 text-foreground">P99 Latency (ms)</td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.ecs?.black_box_metrics?.latency?.p99_ms?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.lambda?.black_box_metrics?.latency?.p99_ms?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {(() => {
                                const ecsValue = benchmarkResultsByBackend.ecs?.black_box_metrics?.latency?.p99_ms
                                const lambdaValue = benchmarkResultsByBackend.lambda?.black_box_metrics?.latency?.p99_ms
                                const diff = calculatePercentageDifference(ecsValue, lambdaValue, true)
                                if (!diff) return '-'
                                return (
                                  <span className={diff.isBetter ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                                    {diff.percentage}% ({diff.faster} faster)
                                </span>
                                )
                              })()}
                            </td>
                          </tr>
                          {/* Success Rate */}
                          <tr className="border-b border-border/30">
                            <td className="p-3 text-foreground">Success Rate</td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.ecs?.black_box_metrics?.request_summary?.success_rate?.toFixed(2) || '-'}%
                            </td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.lambda?.black_box_metrics?.request_summary?.success_rate?.toFixed(2) || '-'}%
                            </td>
                            <td className="p-3 text-right font-mono">
                              {(() => {
                                const ecsValue = benchmarkResultsByBackend.ecs?.black_box_metrics?.request_summary?.success_rate
                                const lambdaValue = benchmarkResultsByBackend.lambda?.black_box_metrics?.request_summary?.success_rate
                                if (ecsValue === undefined || lambdaValue === undefined) return '-'
                                const diff = ecsValue - lambdaValue
                                const isBetter = ecsValue >= lambdaValue
                                return (
                                  <span className={isBetter ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                                    {diff.toFixed(2)}%
                                </span>
                                )
                              })()}
                            </td>
                          </tr>
                          {/* Total Duration */}
                          <tr>
                            <td className="p-3 text-foreground">Total Duration (s)</td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.ecs?.black_box_metrics?.request_summary?.total_duration_seconds?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {benchmarkResultsByBackend.lambda?.black_box_metrics?.request_summary?.total_duration_seconds?.toFixed(2) || '-'}
                            </td>
                            <td className="p-3 text-right font-mono">
                              {(() => {
                                const ecsValue = benchmarkResultsByBackend.ecs?.black_box_metrics?.request_summary?.total_duration_seconds
                                const lambdaValue = benchmarkResultsByBackend.lambda?.black_box_metrics?.request_summary?.total_duration_seconds
                                const diff = calculatePercentageDifference(ecsValue, lambdaValue, true)
                                if (!diff) return '-'
                                return (
                                  <span className={diff.isBetter ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                                    {diff.percentage}% ({diff.faster} faster)
                                </span>
                                )
                              })()}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    {/* Timestamps */}
                    <div className="mt-4 flex gap-6 text-xs text-muted-foreground">
                      {benchmarkResultsByBackend.ecs && (
                        <div>
                          ECS tested: {localStorage.getItem('downloadBenchmarkCompletedAt_ecs')
                            ? new Date(localStorage.getItem('downloadBenchmarkCompletedAt_ecs') || '').toLocaleString()
                            : 'N/A'}
                        </div>
                      )}
                      {benchmarkResultsByBackend.lambda && (
                        <div>
                          Lambda tested: {localStorage.getItem('downloadBenchmarkCompletedAt_lambda')
                            ? new Date(localStorage.getItem('downloadBenchmarkCompletedAt_lambda') || '').toLocaleString()
                            : 'N/A'}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </>
        )}
      </div>
    </main>
  )
}
