import { Link, NavLink } from 'react-router-dom'

export function Nav() {
  return (
    <header className="topbar">
      <Link to="/" className="wordmark">
        Get
      </Link>
      <nav aria-label="Platform">
        <NavLink to="/console">Console</NavLink>
        <NavLink to="/runs">Past runs</NavLink>
      </nav>
    </header>
  )
}
