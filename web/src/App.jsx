import { useEffect } from 'react'
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom'
import Console from './pages/Console.jsx'
import Landing from './pages/Landing.jsx'
import Runs from './pages/Runs.jsx'
import { Nav } from './components/Nav.jsx'
import './styles.css'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

function NotFound() {
  return (
    <div className="page">
      <p className="eyebrow">No such page</p>
      <h1 className="page-title">This route decided nothing.</h1>
      <p className="lede">
        The console and the run history are one click away.
      </p>
      <div className="hero-cta">
        <Link className="button primary" to="/console">
          Open the console
        </Link>
        <Link className="button quiet" to="/">
          Back to the start
        </Link>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Nav />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/console" element={<Console />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
