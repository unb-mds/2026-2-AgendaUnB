import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import App from './App.jsx'
import SecondPage from './pages/SecondPage.jsx'
import PaginaDeEvento from './pages/PaginaDeEvento.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx'
import './styles/global.css'
import './styles/management.css'
const AdminPage = lazy(() => import('./pages/AdminPage.jsx'))
const SuggestionsPage = lazy(() => import('./pages/SuggestionsPage.jsx'))
const TeachingPlanPage = lazy(() => import('./pages/TeachingPlanPage.jsx'))
import { ProtectedRoute } from './components/ManagementUI.jsx'

function LegacyEventsRedirect() {
  const { search, hash } = useLocation();
  return <Navigate replace to={hash === '#plano-de-ensino' ? '/plano-de-ensino' : `/eventos${search}${hash}`} />;
}

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <AuthProvider>
      <Suspense fallback={<div className="management-state" role="status">Carregando página…</div>}><Routes>
        <Route path="/" element={<App />} />
        <Route path="/eventos" element={<SecondPage />} />
        <Route path="/segunda-pagina" element={<LegacyEventsRedirect />} />
        <Route path="/plano-de-ensino" element={<TeachingPlanPage />} />
        <Route path="/evento/:id" element={<PaginaDeEvento />} />
        <Route path="/sugestoes" element={<ProtectedRoute roles={['professor', 'admin']}><SuggestionsPage /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute roles={['admin']}><AdminPage /></ProtectedRoute>} />
      </Routes></Suspense>
    </AuthProvider>
  </BrowserRouter>
)
