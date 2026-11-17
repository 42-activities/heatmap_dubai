import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import App from '../App'

describe('App shell', () => {
  it('renders the four nav links', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )
    for (const name of ['Overview', 'Heatmap', 'Explorer', 'Data']) {
      expect(screen.getByRole('link', { name })).toBeInTheDocument()
    }
  })

  it('renders the matching view for a route', async () => {
    render(
      <MemoryRouter initialEntries={['/heatmap']}>
        <App />
      </MemoryRouter>,
    )
    // Views are lazy-loaded, so the heading appears after the chunk resolves.
    expect(await screen.findByRole('heading', { level: 1, name: 'Heatmap' })).toBeInTheDocument()
  })
})
