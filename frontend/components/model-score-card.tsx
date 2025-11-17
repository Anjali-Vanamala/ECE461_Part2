import { Card } from "@/components/ui/card"

interface ModelScoreCardProps {
  label: string
  value: number
  max: number
  percentage?: boolean
}

export function ModelScoreCard({ label, value, max, percentage }: ModelScoreCardProps) {
  const percentage_val = (value / max) * 100

  let colorClass = "bg-destructive/20"
  if (percentage_val >= 80) colorClass = "bg-chart-3/20"
  else if (percentage_val >= 60) colorClass = "bg-chart-2/20"
  else if (percentage_val >= 40) colorClass = "bg-chart-1/20"

  return (
    <Card className="bg-card/60 border-border/50 backdrop-blur p-4">
      <p className="text-xs text-muted-foreground mb-2">{label}</p>
      <div className="flex items-baseline gap-2">
        <p className="text-2xl font-bold text-foreground">{percentage ? (value * 100).toFixed(0) : value.toFixed(1)}</p>
        <span className="text-xs text-muted-foreground">{percentage ? "%" : `/ ${max}`}</span>
      </div>
      <div className="mt-3 h-2 w-full rounded-full bg-muted/30 overflow-hidden">
        <div className={`h-full rounded-full transition-all ${colorClass}`} style={{ width: `${percentage_val}%` }} />
      </div>
    </Card>
  )
}
