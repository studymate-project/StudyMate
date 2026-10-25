import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import AppLayout from '../components/layout/AppLayout'
import { AuthProvider } from '../auth/AuthContext'
import { AuthGate, ProtectedRoute, PublicOnlyRoute } from '../auth/RouteGuards'
import Spinner from '../components/common/Spinner'

const AskQuestion = lazy(() => import('../pages/AskQuestion'))
const Community = lazy(() => import('../pages/Community'))
const Explore = lazy(() => import('../pages/Explore'))
const Home = lazy(() => import('../pages/Home'))
const NotFound = lazy(() => import('../pages/NotFound'))
const PdfReader = lazy(() => import('../pages/PdfReader'))
const QuestionDetails = lazy(() => import('../pages/QuestionDetails'))
const ResourceDetails = lazy(() => import('../pages/ResourceDetails'))
const SavedResources = lazy(() => import('../pages/SavedResources'))
const SearchResults = lazy(() => import('../pages/SearchResults'))
const UserProfile = lazy(() => import('../pages/UserProfile'))
const VideoDetails = lazy(() => import('../pages/VideoDetails'))
const UploadResource = lazy(() => import('../pages/UploadResource'))
const Notifications = lazy(() => import('../pages/Notifications'))
const Dashboard = lazy(() => import('../pages/Dashboard'))
const StudentProfile = lazy(() => import('../pages/StudentProfile'))
const EditProfile = lazy(() => import('../pages/EditProfile'))
const Login = lazy(() => import('../pages/Login'))
const Signup = lazy(() => import('../pages/Signup'))
const Onboarding = lazy(() => import('../pages/Onboarding'))

function LazyPage({ children }) {
  return <Suspense fallback={<PageLoading />}>{children}</Suspense>
}

function PageLoading() {
  return <div className="flex min-h-[calc(100svh-4rem)] items-center justify-center bg-(--color-bg) px-4" role="status" aria-label="Loading page"><Spinner label="Loading page" /></div>
}

function AppRoutes() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AuthGate>
          <Routes>
            <Route path="login" element={<PublicOnlyRoute><LazyPage><Login /></LazyPage></PublicOnlyRoute>} />
            <Route path="signup" element={<PublicOnlyRoute><LazyPage><Signup /></LazyPage></PublicOnlyRoute>} />
            <Route path="onboarding" element={<ProtectedRoute><LazyPage><Onboarding /></LazyPage></ProtectedRoute>} />
            <Route element={<AppLayout />}>
              <Route index element={<LazyPage><Home /></LazyPage>} />
              <Route path="home" element={<ProtectedRoute><LazyPage><Home /></LazyPage></ProtectedRoute>} />
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
    </BrowserRouter>
  )
}

export default AppRoutes
