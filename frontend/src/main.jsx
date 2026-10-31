import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.jsx'
import SecondPage from './pages/SecondPage.jsx'
import PaginaDeEvento from './pages/PaginaDeEvento.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx'
import './styles/global.css'

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <AuthProvider>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/segunda-pagina" element={<SecondPage />} />
        <Route path="/evento/:id" element={<PaginaDeEvento />} />
      </Routes>
    </AuthProvider>
  </BrowserRouter>
)
