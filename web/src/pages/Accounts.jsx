import { useState } from 'react'
import { Avatar, Button, Card, CardBody, Chip, Input, Modal, ModalBody, ModalContent, ModalFooter, ModalHeader, Progress, Switch, Table, TableBody, TableCell, TableColumn, TableHeader, TableRow, Textarea, Tooltip } from '@heroui/react'
import { Eye, Pencil, Plus, RefreshCw, Trash2, UserRound } from 'lucide-react'
import { api, formatDate, formatNumber } from '../lib/api'
import QuotaCard from '../components/QuotaCard'

const statusMap = {
  active: ['正常', 'success'], disabled: ['已停用', 'default'], rate_limited: ['限流冷却', 'warning'],
  unauthorized: ['鉴权失败', 'danger'], error: ['异常', 'danger'],
}

export default function Accounts({ accounts, onReload, notify }) {
  const [modal, setModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ name: '', token: '' })
  const [saving, setSaving] = useState(false)
  const [busy, setBusy] = useState('')
  const [selected, setSelected] = useState(null)

  const openAdd = () => { setEditing(null); setForm({ name: '', token: '' }); setModal(true) }
  const openEdit = (account) => { setEditing(account); setForm({ name: account.name, token: '' }); setModal(true) }
  const save = async () => {
    if (!editing && !form.token.trim()) return notify('请填写 GitHub OAuth 令牌', 'danger')
    setSaving(true)
    try {
      if (editing) {
        const payload = { name: form.name }
        if (form.token.trim()) payload.token = form.token
        await api(`/api/accounts/${editing.id}`, { method: 'PATCH', body: JSON.stringify(payload) })
        notify('账号已更新')
      } else {
        await api('/api/accounts', { method: 'POST', body: JSON.stringify(form) })
        notify('账号验证成功，已加入账号池')
      }
      setModal(false)
      await onReload()
    } catch (error) { notify(error.message, 'danger') } finally { setSaving(false) }
  }
  const toggle = async (account, enabled) => {
    try { await api(`/api/accounts/${account.id}`, { method: 'PATCH', body: JSON.stringify({ enabled }) }); await onReload() }
    catch (error) { notify(error.message, 'danger') }
  }
  const refresh = async (account) => {
    setBusy(account.id)
    try {
      const updated = await api(`/api/accounts/${account.id}/refresh`, { method: 'POST' })
      if (selected?.id === account.id) setSelected(updated)
      notify('资料与额度已刷新')
      await onReload()
    }
    catch (error) { notify(error.message, 'danger') } finally { setBusy('') }
  }
  const remove = async (account) => {
    if (!window.confirm(`确定删除“${account.name}”吗？本地令牌将一并删除，历史统计会保留。`)) return
    try { await api(`/api/accounts/${account.id}`, { method: 'DELETE' }); setSelected(null); notify('账号已删除'); await onReload() }
    catch (error) { notify(error.message, 'danger') }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="mb-1 text-sm font-medium text-indigo-500">ACCOUNT POOL</p><h1 className="text-3xl font-semibold tracking-tight">账号池</h1><p className="mt-2 text-sm text-default-500">添加 GitHub Copilot 账号，自动调度并跟踪每个账号的额度。</p></div>
        <Button color="primary" startContent={<Plus size={17} />} onPress={openAdd}>添加账号</Button>
      </div>
      <Card className="glass-panel" shadow="none"><CardBody className="px-2 py-2">
        <Table aria-label="Copilot 账号列表" removeWrapper>
          <TableHeader><TableColumn>账号</TableColumn><TableColumn>套餐</TableColumn><TableColumn>状态</TableColumn><TableColumn>聊天额度</TableColumn><TableColumn>请求 / TOKENS</TableColumn><TableColumn>启用</TableColumn><TableColumn align="end">操作</TableColumn></TableHeader>
          <TableBody emptyContent="还没有账号，点击右上角添加" items={accounts}>
            {(account) => {
              const chat = account.quotas?.chat || {}
              const status = statusMap[account.status] || statusMap.error
              return <TableRow key={account.id}>
                <TableCell><div className="flex items-center gap-3 py-2"><Avatar size="sm" src={account.avatar_url} fallback={<UserRound size={16} />} /><div><p className="font-medium">{account.name}</p><p className="text-xs text-default-400">{account.login || account.id.slice(0, 8)}</p></div></div></TableCell>
                <TableCell><Chip size="sm" variant="flat">{account.plan || '未知'}</Chip></TableCell>
                <TableCell><Tooltip content={account.last_error || `上次使用：${formatDate(account.last_used_at)}`}><Chip size="sm" color={status[1]} variant="dot">{status[0]}</Chip></Tooltip></TableCell>
                <TableCell>{chat.unlimited ? <span className="text-success">不限量</span> : <div className="w-28"><p className="mb-1 text-xs">{formatNumber(chat.remaining ?? chat.quota_remaining)} / {formatNumber(chat.entitlement)}</p><Progress size="sm" aria-label="聊天额度" value={chat.entitlement ? (chat.remaining ?? chat.quota_remaining) / chat.entitlement * 100 : 0} /></div>}</TableCell>
                <TableCell><span>{formatNumber(account.request_count)}</span><span className="text-default-400"> / {formatNumber(account.total_tokens)}</span></TableCell>
                <TableCell><Switch size="sm" isSelected={account.enabled} onValueChange={(value) => toggle(account, value)} aria-label="启用账号" /></TableCell>
                <TableCell><div className="flex justify-end gap-1"><Tooltip content="查看额度"><Button isIconOnly size="sm" variant="light" onPress={() => setSelected(account)}><Eye size={16} /></Button></Tooltip><Tooltip content="刷新"><Button isIconOnly size="sm" variant="light" isLoading={busy === account.id} onPress={() => refresh(account)}><RefreshCw size={16} /></Button></Tooltip><Tooltip content="编辑"><Button isIconOnly size="sm" variant="light" onPress={() => openEdit(account)}><Pencil size={16} /></Button></Tooltip><Tooltip content="删除"><Button isIconOnly size="sm" color="danger" variant="light" onPress={() => remove(account)}><Trash2 size={16} /></Button></Tooltip></div></TableCell>
              </TableRow>
            }}
          </TableBody>
        </Table>
      </CardBody></Card>
      {selected && <section><div className="mb-4"><h2 className="text-lg font-semibold">{selected.name} 的额度</h2><p className="mt-1 text-xs text-default-400">重置时间：{selected.quota_reset_date ? formatDate(selected.quota_reset_date) : '以上游返回为准'}</p></div><div className="grid grid-cols-1 gap-4 md:grid-cols-3">{Object.entries(selected.quotas || {}).map(([id, quota]) => <QuotaCard key={id} id={id} quota={quota} />)}</div></section>}

      <Modal isOpen={modal} onOpenChange={setModal} backdrop="blur" placement="center">
        <ModalContent>{(onClose) => <><ModalHeader>{editing ? '编辑账号' : '添加 Copilot 账号'}</ModalHeader><ModalBody>
          <Input label="显示名称" placeholder="例如：个人账号" value={form.name} onValueChange={(name) => setForm({ ...form, name })} />
          <Textarea label={editing ? '更换 OAuth 令牌（留空则不修改）' : 'GitHub OAuth 令牌'} placeholder="gho_... 或 ghu_..." type="password" minRows={3} value={form.token} onValueChange={(token) => setForm({ ...form, token })} description="添加时会调用 GitHub 验证 Copilot 权限并读取额度。令牌仅保存在服务端本地数据库，不会回显。" />
        </ModalBody><ModalFooter><Button variant="light" onPress={onClose}>取消</Button><Button color="primary" isLoading={saving} onPress={save}>{editing ? '保存修改' : '验证并添加'}</Button></ModalFooter></>}</ModalContent>
      </Modal>
    </div>
  )
}
