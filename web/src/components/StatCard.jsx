import { Card, CardBody } from '@heroui/react'

export default function StatCard({ label, value, hint, icon: Icon, tone = 'indigo' }) {
  const tones = {
    indigo: 'bg-indigo-500/10 text-indigo-500',
    cyan: 'bg-cyan-500/10 text-cyan-500',
    emerald: 'bg-emerald-500/10 text-emerald-500',
    amber: 'bg-amber-500/10 text-amber-500',
  }
  return (
    <Card className="glass-panel" shadow="none">
      <CardBody className="flex-row items-center gap-4 p-5">
        <div className={`rounded-2xl p-3 ${tones[tone]}`}><Icon size={22} strokeWidth={1.8} /></div>
        <div className="min-w-0">
          <p className="text-sm text-default-500">{label}</p>
          <p className="mt-0.5 text-2xl font-semibold tracking-tight">{value}</p>
          {hint && <p className="mt-1 truncate text-xs text-default-400">{hint}</p>}
        </div>
      </CardBody>
    </Card>
  )
}
