import { useEffect, useMemo, useState } from 'react'
import { Button, Card, CardBody, Chip, Input, Table, TableBody, TableCell, TableColumn, TableHeader, TableRow } from '@heroui/react'
import { Box, RefreshCw, Search } from 'lucide-react'
import { api, formatNumber } from '../lib/api'

export default function Models({ notify }) {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const load = async () => {
    setLoading(true)
    try { const result = await api('/api/models'); setModels(result.data || []) }
    catch (error) { notify(error.message, 'danger') } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])
  const filtered = useMemo(() => models.filter((model) => `${model.id} ${model.name} ${model.vendor}`.toLowerCase().includes(query.toLowerCase())), [models, query])
  return <div className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="mb-1 text-sm font-medium text-indigo-500">MODEL CATALOG</p><h1 className="text-3xl font-semibold tracking-tight">模型目录</h1><p className="mt-2 text-sm text-default-500">从当前 Copilot 账号实时获取模型、能力和上下文限制。</p></div><Button variant="flat" startContent={<RefreshCw size={16} className={loading ? 'animate-spin' : ''} />} isDisabled={loading} onPress={load}>刷新模型</Button></div>
    <Input className="max-w-md" placeholder="搜索模型、供应商…" startContent={<Search size={16} />} value={query} onValueChange={setQuery} isClearable />
    <Card className="glass-panel" shadow="none"><CardBody className="px-2 py-2"><Table aria-label="模型目录" removeWrapper>
      <TableHeader><TableColumn>模型</TableColumn><TableColumn>供应商</TableColumn><TableColumn>上下文</TableColumn><TableColumn>能力</TableColumn><TableColumn>接口</TableColumn><TableColumn>可用性</TableColumn></TableHeader>
      <TableBody items={filtered} isLoading={loading} emptyContent={query ? '没有匹配的模型' : '暂无模型，请先添加可用账号'}>{(model) => {
        const limits = model.capabilities?.limits || {}
        const supports = model.capabilities?.supports || {}
        const disabled = model.policy?.state === 'disabled'
        return <TableRow key={model.id}>
          <TableCell><div className="flex items-center gap-3 py-2"><div className="rounded-lg bg-indigo-500/10 p-2 text-indigo-500"><Box size={16} /></div><div><p className="font-mono text-xs font-semibold">{model.id}</p><p className="mt-1 text-xs text-default-400">{model.name}</p></div></div></TableCell>
          <TableCell>{model.vendor || '—'}</TableCell><TableCell>{limits.max_context_window_tokens ? `${formatNumber(limits.max_context_window_tokens / 1000)}K` : '—'}</TableCell>
          <TableCell><div className="flex max-w-52 flex-wrap gap-1">{supports.vision && <Chip size="sm" variant="flat">视觉</Chip>}{supports.tool_calls && <Chip size="sm" variant="flat">工具</Chip>}{supports.streaming && <Chip size="sm" variant="flat">流式</Chip>}{supports.structured_outputs && <Chip size="sm" variant="flat">结构化</Chip>}</div></TableCell>
          <TableCell><div className="flex max-w-48 flex-wrap gap-1">{(model.supported_endpoints || ['旧版接口']).map((endpoint) => <Chip key={endpoint} size="sm" variant="bordered" className="font-mono text-[10px]">{endpoint}</Chip>)}</div></TableCell>
          <TableCell><Chip size="sm" color={disabled ? 'default' : 'success'} variant="dot">{disabled ? '未开放' : '可用'}</Chip></TableCell>
        </TableRow>
      }}</TableBody>
    </Table></CardBody></Card>
  </div>
}
