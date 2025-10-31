import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Assessment from './pages/Assessment'
import Results from './pages/Results'
import Dashboard from './pages/Dashboard'
import './styles.css'

function App(){
  return (
    <BrowserRouter>
      <div className="app">
        <header className="site-header">
          <div className="brand">
            <div className="logo">CARES</div>
            <div className="tag">Child AI &amp; Digital Readiness</div>
          </div>
          <nav className="main-nav">
            <Link to="/">Assessment</Link>
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/" className="cta">Start</Link>
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Assessment />} />
            <Route path="/results" element={<Results />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </main>
        <footer className="site-footer">© {new Date().getFullYear()} CARES — For professional use only</footer>
      </div>
    </BrowserRouter>
  )
}

createRoot(document.getElementById('root')).render(<App />)
