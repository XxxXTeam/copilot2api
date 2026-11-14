const TOKEN_KEY = 'copilot2api_admin_token'

export const getAdminToken = () => localStorage.getItem(TOKEN_KEY) || ''
export const setAdminToken = (token) => token
  ? localStorage.setItem(TOKEN_KEY, token)
  : localStorage.removeItem(TOKEN_KEY)

export async function api(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = getAdminToken()
  if (token) headers.set('X-Admin-Key', token)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...options, headers })
  if (response.status === 204) return null
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(data.error?.message || `请求失败 (${response.status})`)
    error.status = response.status
    throw error
  }
  return data
}

export const formatNumber = (value) => new Intl.NumberFormat('zh-CN', {
  maximumFractionDigits: 1,
}).format(Number(value || 0))

export const formatDate = (value) => value
  ? new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
  : '—'
