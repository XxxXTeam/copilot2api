import { useCallback, useEffect, useState } from 'react'
import { Button, Card, CardBody, Chip, Input, Spinner } from '@heroui/react'
import { BookOpen, Box, Github, LayoutDashboard, LogOut, Moon, Sun, Users } from 'lucide-react'
import { api, setAdminToken } from './lib/api'
import Dashboard from './pages/Dashboard'
import Accounts from './pages/Accounts'
import Models from './pages/Models'
import Guide from './pages/Guide'

const navigation = [
  { id: 'dashboard', label: '概览', icon: LayoutDashboard },
  { id: 'accounts', label: '账号池', icon: Users },
  { id: 'models', label: '模型', icon: Box },
  { id: 'guide', label: '接入指南', icon: BookOpen },
]

export default function App() {
  const [page, setPage] = useState('dashboard')
  const [dark, setDark] = useState(true)
  const [overview, setOverview] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loginRequired, setLoginRequired] = useState(false)
  const [token, setToken] = useState('')
  const [notice, setNotice] = useState(null)

  const notify = useCallback((message, color = 'success') => {
    setNotice({ message, color })
    window.setTimeout(() => setNotice(null), 3500)
  }, [])

  const load = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true)
    try {
      const [nextConfig, nextOverview, nextAccounts] = await Promise.all([
        api('/api/config'), api('/api/overview'), api('/api/accounts'),
      ])
      setConfig(nextConfig); setOverview(nextOverview); setAccounts(nextAccounts); setLoginRequired(false)
    } catch (error) {
      if (error.status === 401) setLoginRequired(true)
      else notify(error.message, 'danger')
    } finally { setLoading(false) }
  }, [notify])

  useEffect(() => { load() }, [load])
  useEffect(() => { document.documentElement.classList.toggle('dark', dark) }, [dark])

  const login = async () => {
    setAdminToken(token.trim())
    setToken('')
    await load()
  }
  const logout = () => { setAdminToken(''); setLoginRequired(true); setOverview(null); setAccounts([]) }

  if (loginRequired) return <main className="app-background flex min-h-screen items-center justify-center p-6">
    <Card className="glass-panel w-full max-w-md" shadow="none"><CardBody className="gap-6 p-8">
      <div><div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500 text-white"><Github /></div><h1 className="text-2xl font-semibold">登录 copilot2api</h1><p className="mt-2 text-sm text-default-500">请输入服务端配置的管理令牌。令牌仅保存在当前浏览器。</p></div>
      <Input autoFocus type="password" label="管理令牌" placeholder="COPILOT2API_ADMIN_TOKEN" value={token} onValueChange={setToken} onKeyDown={(event) => event.key === 'Enter' && login()} />
      <Button color="primary" size="lg" isLoading={loading} onPress={login}>进入控制台</Button>
    </CardBody></Card>
  </main>

  return <div className="app-background min-h-screen text-foreground">
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-default-200/60 bg-background/80 px-4 py-6 backdrop-blur-xl lg:flex">
      <div className="mb-10 flex items-center gap-3 px-2"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500 text-white shadow-lg shadow-indigo-500/20"><Github size={21} /></div><div><p className="font-semibold tracking-tight">copilot2api</p><p className="text-[10px] uppercase tracking-widest text-default-400">OpenAI Gateway</p></div></div>
      <nav className="space-y-1">{navigation.map((item) => <Button key={item.id} fullWidth variant={page === item.id ? 'flat' : 'light'} color={page === item.id ? 'primary' : 'default'} className="justify-start" startContent={<item.icon size={18} />} onPress={() => setPage(item.id)}>{item.label}</Button>)}</nav>
      <div className="mt-auto space-y-3"><div className="rounded-xl bg-default-100/70 p-3"><p className="text-xs text-default-400">服务状态</p><div className="mt-2 flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-emerald-500" /><span className="text-xs">运行中 · {accounts.filter((a) => a.enabled).length} 个账号在线</span></div></div><p className="px-2 text-[10px] text-default-300">v0.1.0 · GitHub Copilot</p></div>
    </aside>

    <div className="lg:pl-60">
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-default-200/50 bg-background/75 px-4 backdrop-blur-xl sm:px-8">
        <div className="flex items-center gap-2 lg:hidden"><Github size={20} className="text-indigo-500" /><span className="font-semibold">copilot2api</span></div>
        <div className="hidden items-center gap-2 lg:flex"><span className="text-sm text-default-400">控制台</span><span className="text-default-300">/</span><span className="text-sm">{navigation.find((item) => item.id === page)?.label}</span></div>
        <div className="flex items-center gap-1"><Button isIconOnly variant="light" size="sm" onPress={() => setDark(!dark)} aria-label="切换主题">{dark ? <Sun size={17} /> : <Moon size={17} />}</Button>{config?.admin_auth_required && <Button isIconOnly variant="light" size="sm" onPress={logout} aria-label="退出登录"><LogOut size={17} /></Button>}</div>
      </header>
      <nav className="flex gap-2 overflow-x-auto border-b border-default-200/50 px-4 py-3 lg:hidden">{navigation.map((item) => <Button key={item.id} size="sm" variant={page === item.id ? 'flat' : 'light'} color={page === item.id ? 'primary' : 'default'} startContent={<item.icon size={15} />} onPress={() => setPage(item.id)}>{item.label}</Button>)}</nav>
      <main className="mx-auto max-w-[1500px] p-4 sm:p-6 lg:p-8">
        {loading && !config ? <div className="flex min-h-[60vh] items-center justify-center"><Spinner label="正在读取服务状态…" /></div> : <>
          {page === 'dashboard' && <Dashboard data={overview} loading={loading} onRefresh={() => load(true)} onNavigate={setPage} />}
          {page === 'accounts' && <Accounts accounts={accounts} onReload={() => load(true)} notify={notify} />}
          {page === 'models' && <Models notify={notify} />}
          {page === 'guide' && <Guide config={config} notify={notify} />}
        </>}
      </main>
    </div>
    {notice && <Chip className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 px-4 py-5 shadow-xl" color={notice.color} variant="solid">{notice.message}</Chip>}
  </div>
}
