import { Github, Key, Rocket, Users, Zap } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

export default function Home() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.get('/api/public/stats').then(res => setStats(res.data)).catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
      {/* Header */}
      <header className="container mx-auto px-6 py-4">
        <nav className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Rocket className="text-purple-400 w-8 h-8" />
            <span className="text-2xl font-bold text-white">AntigravityCli</span>
          </div>
          <div className="flex gap-4">
            <Link to="/login" className="px-4 py-2 text-gray-300 hover:text-white transition">
              登录
            </Link>
            <Link to="/register" className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-500 transition">
              注册
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <main className="container mx-auto px-6 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Antigravity
            </span>
            {' '}Token 捐赠云端
          </h1>
          <p className="text-xl text-gray-300 mb-8">
            共享 Antigravity Token，支持 Claude 4.5 / Gemini 3 Pro 等模型
          </p>
          <div className="flex justify-center gap-4">
            <Link to="/register" className="px-8 py-3 bg-purple-600 text-white rounded-lg text-lg font-semibold hover:bg-purple-500 transition flex items-center gap-2">
              <Zap size={20} />
              立即开始
            </Link>
            <a href="https://github.com/liuw1535/antigravity2api-nodejs" target="_blank" rel="noopener noreferrer" className="px-8 py-3 bg-gray-700 text-white rounded-lg text-lg font-semibold hover:bg-gray-600 transition flex items-center gap-2">
              <Github size={20} />
              获取 Token
            </a>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-20 max-w-4xl mx-auto">
            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 text-center">
              <Users className="w-8 h-8 text-purple-400 mx-auto mb-2" />
              <div className="text-3xl font-bold text-white">{stats.users}</div>
              <div className="text-gray-400">用户数</div>
            </div>
            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 text-center">
              <Key className="w-8 h-8 text-green-400 mx-auto mb-2" />
              <div className="text-3xl font-bold text-white">{stats.tokens?.valid || 0}</div>
              <div className="text-gray-400">有效 Token</div>
            </div>
            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 text-center">
              <div className="w-8 h-8 text-cyan-400 mx-auto mb-2 font-bold text-xl">C</div>
              <div className="text-3xl font-bold text-white">{stats.tokens?.claude || 0}</div>
              <div className="text-gray-400">Claude 可用</div>
            </div>
            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-6 text-center">
              <div className="w-8 h-8 text-orange-400 mx-auto mb-2 font-bold text-xl">G</div>
              <div className="text-3xl font-bold text-white">{stats.tokens?.gemini || 0}</div>
              <div className="text-gray-400">Gemini 可用</div>
            </div>
          </div>
        )}

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-20 max-w-5xl mx-auto">
          <div className="bg-gray-800/30 backdrop-blur rounded-xl p-6">
            <div className="w-12 h-12 bg-purple-600/20 rounded-lg flex items-center justify-center mb-4">
              <Key className="text-purple-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Token 池共享</h3>
            <p className="text-gray-400">捐赠 Token 到公共池，所有用户共享使用</p>
          </div>
          <div className="bg-gray-800/30 backdrop-blur rounded-xl p-6">
            <div className="w-12 h-12 bg-green-600/20 rounded-lg flex items-center justify-center mb-4">
              <Zap className="text-green-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">额度奖励</h3>
            <p className="text-gray-400">捐赠 Token 获得额度奖励，支持更多请求</p>
          </div>
          <div className="bg-gray-800/30 backdrop-blur rounded-xl p-6">
            <div className="w-12 h-12 bg-cyan-600/20 rounded-lg flex items-center justify-center mb-4">
              <Rocket className="text-cyan-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">OpenAI 兼容</h3>
            <p className="text-gray-400">完全兼容 OpenAI API 格式，无缝对接</p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-6 py-8 text-center text-gray-500">
        <p>AntigravityCli - Powered by Antigravity API</p>
      </footer>
    </div>
  )
}
