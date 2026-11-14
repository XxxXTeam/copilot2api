import { Button, Card, CardBody, CardHeader, Chip } from '@heroui/react'
import { Check, Copy, KeyRound, Server, ShieldCheck } from 'lucide-react'
import { useState } from 'react'

export default function Guide({ config, notify }) {
  const [copied, setCopied] = useState(false)
  const origin = window.location.port === '5173' ? 'http://127.0.0.1:8000' : window.location.origin
  const example = `curl ${origin}/v1/chat/completions \\\n  -H "Content-Type: application/json" \\\n  -H "Authorization: Bearer YOUR_API_KEY" \\\n  -d '{\n    "model": "gpt-4o-mini",\n    "messages": [{"role": "user", "content": "你好"}],\n    "stream": true\n  }'`
  const copy = async () => { await navigator.clipboard.writeText(example); setCopied(true); notify('示例已复制'); setTimeout(() => setCopied(false), 1500) }
  return <div className="space-y-6">
    <div><p className="mb-1 text-sm font-medium text-indigo-500">GETTING STARTED</p><h1 className="text-3xl font-semibold tracking-tight">接入指南</h1><p className="mt-2 text-sm text-default-500">将任意 OpenAI SDK 的 Base URL 指向本服务即可。</p></div>
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Card className="glass-panel" shadow="none"><CardBody className="gap-3 p-5"><Server className="text-indigo-500" /><p className="font-medium">OpenAI Base URL</p><code className="break-all text-xs text-default-400">{origin}/v1</code></CardBody></Card>
      <Card className="glass-panel" shadow="none"><CardBody className="gap-3 p-5"><KeyRound className="text-cyan-500" /><p className="font-medium">API Key 鉴权</p><p className="text-xs text-default-400">{config?.api_auth_required ? '已启用，请在请求中携带配置的 API Key。' : '当前未启用，可通过环境变量开启。'}</p></CardBody></Card>
      <Card className="glass-panel" shadow="none"><CardBody className="gap-3 p-5"><ShieldCheck className="text-emerald-500" /><p className="font-medium">隐私与日志</p><p className="text-xs text-default-400">不存储聊天正文，仅记录模型、Token 用量和错误信息。</p></CardBody></Card>
    </div>
    <Card className="glass-panel" shadow="none"><CardHeader className="justify-between px-5 pt-5"><div><h2 className="font-semibold">聊天请求示例</h2><p className="mt-1 text-xs text-default-400">未配置 API Key 时可省略 Authorization 请求头</p></div><Button isIconOnly size="sm" variant="flat" onPress={copy}>{copied ? <Check size={16} /> : <Copy size={16} />}</Button></CardHeader><CardBody className="px-5 pb-5"><pre className="code-block rounded-xl bg-default-100 p-4 text-default-600">{example}</pre></CardBody></Card>
    <Card className="glass-panel" shadow="none"><CardBody className="gap-4 p-5"><h2 className="font-semibold">服务配置</h2><div className="grid gap-3 text-sm sm:grid-cols-2"><div className="flex justify-between rounded-xl bg-default-100/60 p-3"><span className="text-default-500">账号池策略</span><Chip size="sm" variant="flat">{config?.strategy || '—'}</Chip></div><div className="flex justify-between rounded-xl bg-default-100/60 p-3"><span className="text-default-500">请求超时</span><span>{config?.request_timeout || '—'} 秒</span></div></div><p className="text-xs leading-6 text-default-400">可通过 COPILOT2API_API_KEYS、COPILOT2API_ADMIN_TOKEN、COPILOT2API_POOL_STRATEGY 等环境变量调整。修改后需重启服务；详细说明见项目 README。</p></CardBody></Card>
  </div>
}
