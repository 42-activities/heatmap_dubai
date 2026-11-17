import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'

// Route-level code splitting: Overview pulls in Recharts and Heatmap pulls in
// Leaflet, so lazy-loading each view keeps them out of the initial bundle.
const Overview = lazy(() => import('./views/Overview'))
const Heatmap = lazy(() => import('./views/Heatmap'))
const Explorer = lazy(() => import('./views/Explorer'))
const Data = lazy(() => import('./views/Data'))

export default function App() {
  return (
    <Layout>
      <Suspense fallback={<p role="status">Loading…</p>}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/heatmap" element={<Heatmap />} />
          <Route path="/explorer" element={<Explorer />} />
          <Route path="/data" element={<Data />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}
