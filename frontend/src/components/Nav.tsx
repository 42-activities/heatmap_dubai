import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Overview', end: true },
  { to: '/heatmap', label: 'Heatmap', end: false },
  { to: '/explorer', label: 'Explorer', end: false },
  { to: '/data', label: 'Data', end: false },
]

export default function Nav() {
  return (
    <nav className="nav" aria-label="Primary">
      <span className="nav__brand">Dubai Bus Analytics</span>
      <ul className="nav__links">
        {links.map((l) => (
          <li key={l.to}>
            <NavLink to={l.to} end={l.end} className={({ isActive }) => (isActive ? 'active' : '')}>
              {l.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
