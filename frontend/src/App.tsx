import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './views/Overview'
import Heatmap from './views/Heatmap'
import Explorer from './views/Explorer'
import Data from './views/Data'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/heatmap" element={<Heatmap />} />
        <Route path="/explorer" element={<Explorer />} />
        <Route path="/data" element={<Data />} />
      </Routes>
    </Layout>
  )
}
