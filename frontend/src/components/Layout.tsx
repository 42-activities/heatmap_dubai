import type { ReactNode } from 'react'
import Nav from './Nav'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="layout">
      <Nav />
      <main className="layout__main">{children}</main>
    </div>
  )
}
