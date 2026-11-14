import { Card, CardBody, Chip, Progress } from '@heroui/react'
import { formatNumber } from '../lib/api'

const labels = {
  chat: '聊天请求',
  completions: '代码补全',
  premium_interactions: '高级模型交互',
}

export default function QuotaCard({ id, quota }) {
  const remaining = quota.remaining ?? quota.quota_remaining ?? 0
  const entitlement = quota.entitlement || 0
  const percent = quota.unlimited ? 100 : entitlement > 0 ? Math.max(0, Math.min(100, remaining / entitlement * 100)) : 0
  return (
    <Card className="glass-panel" shadow="none">
      <CardBody className="gap-4 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">{labels[id] || id}</p>
            <p className="mt-1 text-xs text-default-400">{quota.accounts ? `${quota.accounts} 个账号合计` : '当前账号'}</p>
          </div>
          {quota.unlimited && <Chip size="sm" color="success" variant="flat">不限量</Chip>}
        </div>
        <div className="flex items-end justify-between gap-4">
          <p className="text-2xl font-semibold">{quota.unlimited ? '∞' : formatNumber(remaining)}</p>
          <p className="pb-1 text-xs text-default-400">总额度 {quota.unlimited ? '∞' : formatNumber(entitlement)}</p>
        </div>
        <Progress aria-label="剩余额度" value={percent} color={percent < 20 ? 'danger' : percent < 50 ? 'warning' : 'primary'} size="sm" />
      </CardBody>
    </Card>
  )
}
