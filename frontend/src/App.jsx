import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const savedUser = localStorage.getItem('user')
    if (savedUser) {
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  const handleLogin = (userData, token) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(userData))
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">加载中...</div>
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route 
        path="/login" 
        element={user ? <Navigate to="/dashboard" /> : <Login onLogin={handleLogin} />} 
      />
      <Route 
        path="/register" 
        element={user ? <Navigate to="/dashboard" /> : <Register onLogin={handleLogin} />} 
      />
      <Route 
        path="/dashboard" 
        element={user ? <Dashboard user={user} onLogout={handleLogout} setUser={setUser} /> : <Navigate to="/login" />} 
      />
    </Routes>
  )
}

export default App
