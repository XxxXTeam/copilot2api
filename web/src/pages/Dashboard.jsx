import { Button, Card, CardBody, CardHeader, Chip, Table, TableBody, TableCell, TableColumn, TableHeader, TableRow } from '@heroui/react'
import { Activity, ArrowRight, CheckCircle2, Coins, RefreshCw, Users, XCircle, Zap } from 'lucide-react'
import StatCard from '../components/StatCard'
import QuotaCard from '../components/QuotaCard'
import { formatDate, formatNumber } from '../lib/api'

export default function Dashboard({ data, loading, onRefresh, onNavigate }) {
  const quotas = Object.entries(data?.quotas || {})
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-sm font-medium text-indigo-500">OVERVIEW</p>
          <h1 className="text-3xl font-semibold tracking-tight">运行概览</h1>
          <p className="mt-2 text-sm text-default-500">账号健康度、调用情况与 Copilot 额度一目了然。</p>
        </div>
        <Button variant="flat" startContent={<RefreshCw size={16} className={loading ? 'animate-spin' : ''} />} onPress={onRefresh} isDisabled={loading}>刷新数据</Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="账号总数" value={data?.accounts ?? '—'} hint={`${data?.enabled_accounts || 0} 个已启用`} icon={Users} />
        <StatCard label="健康账号" value={data?.healthy_accounts ?? '—'} hint="可参与请求调度" icon={CheckCircle2} tone="emerald" />
        <StatCard label="累计请求" value={formatNumber(data?.total_requests)} hint={`今日 ${formatNumber(data?.today_requests)} 次`} icon={Activity} tone="cyan" />
        <StatCard label="消耗 Tokens" value={formatNumber(data?.total_tokens)} hint="基于上游 usage 统计" icon={Coins} tone="amber" />
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <div><h2 className="text-lg font-semibold">额度总览</h2><p className="mt-1 text-xs text-default-400">所有已启用账号的剩余额度合计</p></div>
          <Button size="sm" variant="light" endContent={<ArrowRight size={14} />} onPress={() => onNavigate('accounts')}>管理账号</Button>
        </div>
        {quotas.length ? <div className="grid grid-cols-1 gap-4 md:grid-cols-3">{quotas.map(([id, quota]) => <QuotaCard key={id} id={id} quota={quota} />)}</div> : (
          <Card className="glass-panel border-dashed" shadow="none"><CardBody className="items-center py-10 text-center"><Zap className="mb-3 text-default-300" /><p className="text-sm text-default-500">添加账号并刷新后，这里会显示额度</p></CardBody></Card>
        )}
      </section>

      <Card className="glass-panel" shadow="none">
        <CardHeader className="flex-col items-start gap-1 px-5 pb-2 pt-5"><h2 className="text-lg font-semibold">最近请求</h2><p className="text-xs text-default-400">仅保存调用元数据，不记录聊天内容</p></CardHeader>
        <CardBody className="px-2 pt-2">
          <Table aria-label="最近请求" removeWrapper shadow="none">
            <TableHeader><TableColumn>模型</TableColumn><TableColumn>账号</TableColumn><TableColumn>TOKENS</TableColumn><TableColumn>状态</TableColumn><TableColumn>时间</TableColumn></TableHeader>
            <TableBody emptyContent="暂无请求记录" items={data?.recent_requests || []}>
              {(item) => <TableRow key={item.id}>
                <TableCell><span className="font-mono text-xs">{item.model}</span></TableCell>
                <TableCell>{item.account_name}</TableCell>
                <TableCell>{formatNumber(item.total_tokens)}</TableCell>
                <TableCell>{item.success ? <Chip size="sm" color="success" variant="flat" startContent={<CheckCircle2 size={12} />}>成功</Chip> : <Chip size="sm" color="danger" variant="flat" startContent={<XCircle size={12} />}>失败</Chip>}</TableCell>
                <TableCell className="text-default-400">{formatDate(item.created_at)}</TableCell>
              </TableRow>}
            </TableBody>
          </Table>
        </CardBody>
      </Card>
    </div>
  )
}
