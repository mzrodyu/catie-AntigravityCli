import {
    CheckCircle,
    Copy,
    ExternalLink,
    Gift,
    Key,
    LogOut,
    Plus,
    RefreshCw,
    Rocket,
    Trash2,
    XCircle
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

export default function Dashboard({ user, onLogout, setUser }) {
  const [tokens, setTokens] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [showOAuth, setShowOAuth] = useState(false)
  const [showManual, setShowManual] = useState(false)
  const [newToken, setNewToken] = useState('')
  const [isPublic, setIsPublic] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState(null)
  const [oauthUrl, setOauthUrl] = useState('')
  const [callbackUrl, setCallbackUrl] = useState('')
  const [manualToken, setManualToken] = useState({ access_token: '', refresh_token: '', expires_in: 3600 })
  const navigate = useNavigate()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [tokensRes, statsRes, meRes] = await Promise.all([
        api.get('/api/auth/tokens'),
        api.get('/api/public/stats'),
        api.get('/api/auth/me')
      ])
      setTokens(tokensRes.data)
      setStats(statsRes.data)
      setUser(meRes.data)
      localStorage.setItem('user', JSON.stringify(meRes.data))
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    setUploading(true)
    setMessage(null)

    try {
      const formData = new FormData()
      formData.append('token', newToken)
      formData.append('is_public', isPublic)

      const res = await api.post('/api/auth/tokens', formData)
      setMessage({ type: 'success', text: `Token 上传成功！支持: ${res.data.supports_claude ? 'Claude ' : ''}${res.data.supports_gemini ? 'Gemini' : ''}` })
      setNewToken('')
      setShowUpload(false)
      loadData()
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || '上传失败' })
    } finally {
      setUploading(false)
    }
  }

  const togglePublic = async (tokenId, currentPublic) => {
    try {
      const formData = new FormData()
      formData.append('is_public', !currentPublic)
      await api.patch(`/api/auth/tokens/${tokenId}`, formData)
      loadData()
    } catch (err) {
      alert(err.response?.data?.detail || '操作失败')
    }
  }

  const deleteToken = async (tokenId) => {
    if (!confirm('确定要删除这个 Token 吗？')) return
    try {
      await api.delete(`/api/auth/tokens/${tokenId}`)
      loadData()
    } catch (err) {
      alert(err.response?.data?.detail || '删除失败')
    }
  }

  const copyApiKey = () => {
    const apiKey = `sk-${localStorage.getItem('token')?.slice(0, 32)}`
    navigator.clipboard.writeText(apiKey)
    setMessage({ type: 'success', text: 'API Key 已复制' })
    setTimeout(() => setMessage(null), 2000)
  }

  // OAuth 登录
  const startOAuth = async () => {
    try {
      const res = await api.get('/api/oauth/auth-url')
      setOauthUrl(res.data.auth_url)
      setShowOAuth(true)
      window.open(res.data.auth_url, '_blank')
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'OAuth 初始化失败' })
    }
  }

  // 提交 OAuth 回调
  const submitOAuthCallback = async () => {
    if (!callbackUrl) return
    setUploading(true)
    try {
      const res = await api.post('/api/oauth/callback', {
        callback_url: callbackUrl,
        is_public: isPublic
      })
      setMessage({ type: 'success', text: `凭证获取成功！邮箱: ${res.data.email}` })
      setShowOAuth(false)
      setCallbackUrl('')
      loadData()
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || '回调处理失败' })
    } finally {
      setUploading(false)
    }
  }

  // 手动填入 Token
  const submitManualToken = async () => {
    if (!manualToken.access_token || !manualToken.refresh_token) return
    setUploading(true)
    try {
      const res = await api.post('/api/oauth/manual', {
        ...manualToken,
        is_public: isPublic
      })
      setMessage({ type: 'success', text: `Token 添加成功！${res.data.email ? `邮箱: ${res.data.email}` : ''}` })
      setShowManual(false)
      setManualToken({ access_token: '', refresh_token: '', expires_in: 3600 })
      loadData()
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || '添加失败' })
    } finally {
      setUploading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white">加载中...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="container mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Rocket className="text-purple-400 w-8 h-8" />
            <span className="text-xl font-bold text-white">AntigravityCli</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">
              {user.username} | 额度: <span className="text-green-400">{user.daily_quota}</span>
            </span>
            <button
              onClick={onLogout}
              className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 flex items-center gap-2"
            >
              <LogOut size={18} />
              退出
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {message && (
          <div className={`mb-6 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-600/20 text-green-400' : 'bg-red-600/20 text-red-400'}`}>
            {message.text}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-800 rounded-xl p-4">
            <div className="text-gray-400 text-sm">我的额度</div>
            <div className="text-2xl font-bold text-green-400">{user.daily_quota}</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4">
            <div className="text-gray-400 text-sm">我的 Token</div>
            <div className="text-2xl font-bold text-purple-400">{tokens.length}</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4">
            <div className="text-gray-400 text-sm">公共池 Token</div>
            <div className="text-2xl font-bold text-cyan-400">{stats?.tokens?.valid || 0}</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4">
            <div className="text-gray-400 text-sm">今日请求</div>
            <div className="text-2xl font-bold text-orange-400">{stats?.today_requests || 0}</div>
          </div>
        </div>

        {/* API Key */}
        <div className="bg-gray-800 rounded-xl p-6 mb-8">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Key className="text-purple-400" />
            API 接入
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="text-gray-400 text-sm">API Base URL</label>
              <div className="flex gap-2 mt-1">
                <input
                  type="text"
                  value={`${window.location.origin}/v1`}
                  readOnly
                  className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2"
                />
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(`${window.location.origin}/v1`)
                    setMessage({ type: 'success', text: 'URL 已复制' })
                    setTimeout(() => setMessage(null), 2000)
                  }}
                  className="px-3 py-2 bg-gray-600 rounded-lg hover:bg-gray-500"
                >
                  <Copy size={18} className="text-white" />
                </button>
              </div>
            </div>
            <div>
              <label className="text-gray-400 text-sm">API Key</label>
              <div className="flex gap-2 mt-1">
                <input
                  type="password"
                  value="sk-••••••••••••••••"
                  readOnly
                  className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2"
                />
                <button
                  onClick={copyApiKey}
                  className="px-3 py-2 bg-purple-600 rounded-lg hover:bg-purple-500"
                >
                  <Copy size={18} className="text-white" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Tokens */}
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Key className="text-purple-400" />
              我的 Token ({tokens.length})
            </h2>
            <div className="flex gap-2">
              <button
                onClick={loadData}
                className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 flex items-center gap-2"
              >
                <RefreshCw size={18} />
                刷新
              </button>
              <button
                onClick={startOAuth}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 flex items-center gap-2"
              >
                <Rocket size={18} />
                OAuth 登录
              </button>
              <button
                onClick={() => setShowManual(true)}
                className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-500 flex items-center gap-2"
              >
                <Key size={18} />
                手动填入
              </button>
              <button
                onClick={() => setShowUpload(true)}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 flex items-center gap-2"
              >
                <Plus size={18} />
                上传 Token
              </button>
            </div>
          </div>

          {/* OAuth Modal */}
          {showOAuth && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg mx-4">
                <h3 className="text-xl font-semibold text-white mb-4">OAuth 登录获取凭证</h3>
                <div className="mb-4">
                  <p className="text-gray-400 text-sm mb-3">
                    1. 点击下方按钮打开 Google 授权页面<br/>
                    2. 完成授权后，复制浏览器地址栏的完整 URL<br/>
                    3. 粘贴到下方输入框并提交
                  </p>
                  <button
                    onClick={() => window.open(oauthUrl, '_blank')}
                    className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 mb-4"
                  >
                    打开授权页面
                  </button>
                  <label className="text-gray-400 text-sm mb-2 block">回调 URL</label>
                  <input
                    type="text"
                    value={callbackUrl}
                    onChange={(e) => setCallbackUrl(e.target.value)}
                    className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="粘贴 http://localhost:8080/?code=... 的完整 URL"
                  />
                </div>
                <div className="mb-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isPublic}
                      onChange={(e) => setIsPublic(e.target.checked)}
                      className="w-5 h-5 rounded bg-gray-700"
                    />
                    <span className="text-white">捐赠到公共池（获得额度奖励）</span>
                  </label>
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => { setShowOAuth(false); setCallbackUrl(''); }}
                    className="flex-1 px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600"
                  >
                    取消
                  </button>
                  <button
                    onClick={submitOAuthCallback}
                    disabled={uploading || !callbackUrl}
                    className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 disabled:opacity-50"
                  >
                    {uploading ? '处理中...' : '提交'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Manual Token Modal */}
          {showManual && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg mx-4">
                <h3 className="text-xl font-semibold text-white mb-4">手动填入 Token</h3>
                <div className="space-y-4 mb-4">
                  <div>
                    <label className="text-gray-400 text-sm mb-2 block">Access Token</label>
                    <textarea
                      value={manualToken.access_token}
                      onChange={(e) => setManualToken({...manualToken, access_token: e.target.value})}
                      className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 h-20 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                      placeholder="ya29.xxxxx..."
                    />
                  </div>
                  <div>
                    <label className="text-gray-400 text-sm mb-2 block">Refresh Token</label>
                    <textarea
                      value={manualToken.refresh_token}
                      onChange={(e) => setManualToken({...manualToken, refresh_token: e.target.value})}
                      className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 h-20 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                      placeholder="1//xxxxx..."
                    />
                  </div>
                  <div>
                    <label className="text-gray-400 text-sm mb-2 block">过期时间（秒）</label>
                    <input
                      type="number"
                      value={manualToken.expires_in}
                      onChange={(e) => setManualToken({...manualToken, expires_in: parseInt(e.target.value) || 3600})}
                      className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                    />
                  </div>
                </div>
                <div className="mb-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isPublic}
                      onChange={(e) => setIsPublic(e.target.checked)}
                      className="w-5 h-5 rounded bg-gray-700"
                    />
                    <span className="text-white">捐赠到公共池（获得额度奖励）</span>
                  </label>
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => { setShowManual(false); setManualToken({ access_token: '', refresh_token: '', expires_in: 3600 }); }}
                    className="flex-1 px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600"
                  >
                    取消
                  </button>
                  <button
                    onClick={submitManualToken}
                    disabled={uploading || !manualToken.access_token || !manualToken.refresh_token}
                    className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-500 disabled:opacity-50"
                  >
                    {uploading ? '添加中...' : '添加'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Upload Modal */}
          {showUpload && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md mx-4">
                <h3 className="text-xl font-semibold text-white mb-4">上传 Token</h3>
                <form onSubmit={handleUpload}>
                  <div className="mb-4">
                    <label className="text-gray-400 text-sm mb-2 block">Antigravity Token</label>
                    <textarea
                      value={newToken}
                      onChange={(e) => setNewToken(e.target.value)}
                      className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 h-32 focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="粘贴你的 Antigravity Token..."
                      required
                    />
                  </div>
                  <div className="mb-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isPublic}
                        onChange={(e) => setIsPublic(e.target.checked)}
                        className="w-5 h-5 rounded bg-gray-700"
                      />
                      <span className="text-white">捐赠到公共池（获得额度奖励）</span>
                    </label>
                  </div>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setShowUpload(false)}
                      className="flex-1 px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600"
                    >
                      取消
                    </button>
                    <button
                      type="submit"
                      disabled={uploading}
                      className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 disabled:opacity-50"
                    >
                      {uploading ? '验证中...' : '上传'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Token List */}
          {tokens.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Key className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>还没有上传任何 Token</p>
              <p className="text-sm mt-2">
                <a href="https://github.com/liuw1535/antigravity2api-nodejs" target="_blank" className="text-purple-400 hover:text-purple-300 flex items-center justify-center gap-1">
                  获取 Antigravity Token <ExternalLink size={14} />
                </a>
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {tokens.map(token => (
                <div key={token.id} className="bg-gray-700/50 rounded-lg p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {token.is_active ? (
                      <CheckCircle className="text-green-400" />
                    ) : (
                      <XCircle className="text-red-400" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">Token #{token.id}</span>
                        {token.supports_claude && (
                          <span className="px-2 py-0.5 bg-cyan-600/30 text-cyan-400 text-xs rounded">Claude</span>
                        )}
                        {token.supports_gemini && (
                          <span className="px-2 py-0.5 bg-orange-600/30 text-orange-400 text-xs rounded">Gemini</span>
                        )}
                        {token.is_public && (
                          <span className="px-2 py-0.5 bg-purple-600/30 text-purple-400 text-xs rounded">公共池</span>
                        )}
                      </div>
                      <div className="text-gray-400 text-sm">
                        成功: {token.success_count} | 失败: {token.failure_count}
                        {token.last_error && <span className="text-red-400 ml-2">| {token.last_error}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => togglePublic(token.id, token.is_public)}
                      className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 ${
                        token.is_public 
                          ? 'bg-gray-600 text-gray-300 hover:bg-gray-500' 
                          : 'bg-purple-600 text-white hover:bg-purple-500'
                      }`}
                    >
                      <Gift size={14} />
                      {token.is_public ? '取消捐赠' : '捐赠'}
                    </button>
                    <button
                      onClick={() => deleteToken(token.id)}
                      className="px-3 py-1.5 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
