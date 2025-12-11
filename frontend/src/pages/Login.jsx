import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Rocket, LogIn } from 'lucide-react'
import api from '../api'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const formData = new FormData()
      formData.append('username', username)
      formData.append('password', password)

      const res = await api.post('/api/auth/login', formData)
      onLogin(res.data.user, res.data.access_token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 text-white">
            <Rocket className="text-purple-400 w-10 h-10" />
            <span className="text-3xl font-bold">AntigravityCli</span>
          </Link>
        </div>

        <div className="bg-gray-800 rounded-2xl p-8 shadow-xl">
          <h2 className="text-2xl font-bold text-white mb-6 text-center">登录账号</h2>

          {error && (
            <div className="mb-4 p-3 bg-red-600/20 border border-red-600 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-gray-400 text-sm mb-2">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="输入用户名"
                required
              />
            </div>
            <div>
              <label className="block text-gray-400 text-sm mb-2">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-gray-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="输入密码"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-purple-600 text-white rounded-lg py-3 font-semibold hover:bg-purple-500 transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <LogIn size={20} />
              {loading ? '登录中...' : '登录'}
            </button>
          </form>

          <p className="mt-6 text-center text-gray-400">
            没有账号？
            <Link to="/register" className="text-purple-400 hover:text-purple-300 ml-1">
              立即注册
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
