import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, lazy, Suspense } from 'react'
import { useAuthStore } from './store/auth'
import { authApi } from './api/auth'
import { Layout } from './components/layout/Layout'
import { Toaster } from './components/ui/Toaster'
import { Spinner } from './components/ui/Spinner'

// Code-splitting por ruta: cada página es su propio chunk. Así la landing
// (pesada) y recharts (solo en DomainDetail) no cargan en el arranque del panel.
const Landing      = lazy(() => import('./pages/Landing').then(m => ({ default: m.Landing })))
const Login        = lazy(() => import('./pages/Login').then(m => ({ default: m.Login })))
const Register     = lazy(() => import('./pages/Register').then(m => ({ default: m.Register })))
const VerifyEmail  = lazy(() => import('./pages/VerifyEmail').then(m => ({ default: m.VerifyEmail })))
const VerifyPending = lazy(() => import('./pages/VerifyPending').then(m => ({ default: m.VerifyPending })))
const ForgotPassword = lazy(() => import('./pages/ForgotPassword').then(m => ({ default: m.ForgotPassword })))
const ResetPassword = lazy(() => import('./pages/ResetPassword').then(m => ({ default: m.ResetPassword })))
const Dashboard    = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })))
const Domains      = lazy(() => import('./pages/Domains').then(m => ({ default: m.Domains })))
const DomainDetail = lazy(() => import('./pages/DomainDetail').then(m => ({ default: m.DomainDetail })))
const Account      = lazy(() => import('./pages/Account').then(m => ({ default: m.Account })))
const BillingSuccess = lazy(() => import('./pages/BillingSuccess').then(m => ({ default: m.BillingSuccess })))
const Terms        = lazy(() => import('./pages/Legal').then(m => ({ default: m.Terms })))
const Privacy      = lazy(() => import('./pages/Legal').then(m => ({ default: m.Privacy })))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function PageFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <Spinner size="lg" />
    </div>
  )
}

function RequireAuth() {
  const { accessToken, user, setAuth, clearAuth } = useAuthStore()

  useEffect(() => {
    if (accessToken && !user) {
      authApi.me()
        .then(r => setAuth(r.data, accessToken, localStorage.getItem('refresh_token') ?? ''))
        .catch(() => clearAuth())
    }
  }, [accessToken, user, setAuth, clearAuth])

  if (!accessToken) return <Navigate to="/login" replace />
  return <Outlet />
}

const router = createBrowserRouter([
  { path: '/',             element: <Landing /> },
  { path: '/login',        element: <Login /> },
  { path: '/register',     element: <Register /> },
  { path: '/verify-email', element: <VerifyEmail /> },
  { path: '/verify-pending', element: <VerifyPending /> },
  // Las dos mitades del flujo de recuperación. La ruta
  // /reset-password es la que enlaza el correo que manda el backend
  // (services/email.py): sin ella el enlace caía en el catch-all `*`
  // y el usuario terminaba en la landing sin explicación.
  { path: '/forgot-password', element: <ForgotPassword /> },
  { path: '/reset-password',  element: <ResetPassword /> },
  { path: '/legal/terminos',   element: <Terms /> },
  { path: '/legal/privacidad', element: <Privacy /> },
  {
    element: <RequireAuth />,
    children: [{
      element: <Layout />,
      children: [
        { path: '/dashboard',     element: <Dashboard /> },
        { path: '/domains',       element: <Domains /> },
        { path: '/domains/new',   element: <Navigate to="/domains" replace /> },
        { path: '/domains/:id',   element: <DomainDetail /> },
        { path: '/account',       element: <Account /> },
        { path: '/billing/success', element: <BillingSuccess /> },
      ],
    }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={<PageFallback />}>
        <RouterProvider router={router} />
      </Suspense>
      <Toaster />
    </QueryClientProvider>
  )
}
