import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import AppLayout from '../components/layout/AppLayout'
import { AuthProvider } from '../auth/AuthContext'
import { AuthGate, ProtectedRoute, PublicOnlyRoute } from '../auth/RouteGuards'
import { useAuth } from '../auth/useAuth'
import { queryClient } from '../query/queryClient'
import routeLoaders from './routeLoaders'

const AskQuestion = lazy(routeLoaders.askQuestion)
const Community = lazy(routeLoaders.community)
const Explore = lazy(routeLoaders.explore)
const Home = lazy(routeLoaders.home)
const NotFound = lazy(routeLoaders.notFound)
const PdfReader = lazy(routeLoaders.pdfReader)
const QuestionDetails = lazy(routeLoaders.questionDetails)
const ResourceDetails = lazy(routeLoaders.resourceDetails)
const SavedResources = lazy(routeLoaders.savedResources)
const SearchResults = lazy(routeLoaders.searchResults)
const UserProfile = lazy(routeLoaders.userProfile)
const VideoDetails = lazy(routeLoaders.videoDetails)
const UploadResource = lazy(routeLoaders.uploadResource)
const Notifications = lazy(routeLoaders.notifications)
const Dashboard = lazy(routeLoaders.dashboard)
const StudentProfile = lazy(routeLoaders.studentProfile)
const EditProfile = lazy(routeLoaders.editProfile)
const Login = lazy(routeLoaders.login)
const Signup = lazy(routeLoaders.signup)
const Onboarding = lazy(routeLoaders.onboarding)

function LazyPage({ children }) {
  return <Suspense fallback={<PageLoading />}>{children}</Suspense>
}

function PageLoading() {
  return (
    <div className="mx-auto w-full max-w-[1260px] animate-pulse px-5 py-8 sm:px-8 lg:px-10" role="status" aria-label="Loading page">
      <div className="h-8 w-2/5 rounded-lg bg-[var(--color-surface-muted)]" />
      <div className="mt-3 h-4 w-3/5 rounded bg-[var(--color-surface-muted)]" />
      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((item) => <div key={item} className="h-40 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]" />)}
      </div>
    </div>
  )
}

function CanonicalHomePage() {
  const { status, user } = useAuth()

  if (status === 'authenticated' && !user?.profile?.onboarding_completed) {
    return <Navigate to="/onboarding" replace />
  }

  return <LazyPage><Home /></LazyPage>
}

function AppRoutes() {
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AuthGate>
            <Routes>
            <Route path="login" element={<PublicOnlyRoute><LazyPage><Login /></LazyPage></PublicOnlyRoute>} />
            <Route path="signup" element={<PublicOnlyRoute><LazyPage><Signup /></LazyPage></PublicOnlyRoute>} />
            <Route path="onboarding" element={<ProtectedRoute><LazyPage><Onboarding /></LazyPage></ProtectedRoute>} />
            <Route element={<AppLayout />}>
              <Route index element={<CanonicalHomePage />} />
              <Route path="home" element={<ProtectedRoute><Navigate to="/" replace /></ProtectedRoute>} />
              <Route path="explore" element={<LazyPage><Explore /></LazyPage>} />
              <Route path="resources/:slug/read" element={<LazyPage><PdfReader /></LazyPage>} />
              <Route path="resources/:slug" element={<LazyPage><ResourceDetails /></LazyPage>} />
              <Route path="videos/:slug" element={<LazyPage><VideoDetails /></LazyPage>} />
              <Route path="search" element={<LazyPage><SearchResults /></LazyPage>} />
              <Route path="saved" element={<ProtectedRoute><LazyPage><SavedResources /></LazyPage></ProtectedRoute>} />
              <Route path="community" element={<LazyPage><Community /></LazyPage>} />
              <Route path="community/ask" element={<ProtectedRoute><LazyPage><AskQuestion /></LazyPage></ProtectedRoute>} />
              <Route path="questions/:slug" element={<LazyPage><QuestionDetails /></LazyPage>} />
              <Route path="users/:username" element={<LazyPage><UserProfile /></LazyPage>} />
              <Route path="pdf/:slug" element={<LazyPage><PdfReader /></LazyPage>} />
              <Route path="upload" element={<ProtectedRoute><LazyPage><UploadResource /></LazyPage></ProtectedRoute>} />
              <Route path="notifications" element={<ProtectedRoute><LazyPage><Notifications /></LazyPage></ProtectedRoute>} />
              <Route path="dashboard" element={<ProtectedRoute><LazyPage><Dashboard /></LazyPage></ProtectedRoute>} />
              <Route path="profile" element={<ProtectedRoute><LazyPage><StudentProfile /></LazyPage></ProtectedRoute>} />
              <Route path="profile/edit" element={<ProtectedRoute><LazyPage><EditProfile /></LazyPage></ProtectedRoute>} />
              <Route path="profile/:username" element={<LazyPage><UserProfile /></LazyPage>} />
              <Route path="community/questions/:slug" element={<LazyPage><QuestionDetails /></LazyPage>} />
              <Route path="*" element={<LazyPage><NotFound /></LazyPage>} />
            </Route>
            </Routes>
          </AuthGate>
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}

export default AppRoutes
