import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AppLayout from '../components/layout/AppLayout'
import AskQuestion from '../pages/AskQuestion'
import Community from '../pages/Community'
import Explore from '../pages/Explore'
import Home from '../pages/Home'
import NotFound from '../pages/NotFound'
import PdfReader from '../pages/PdfReader'
import QuestionDetails from '../pages/QuestionDetails'
import ResourceDetails from '../pages/ResourceDetails'
import SavedResources from '../pages/SavedResources'
import SearchResults from '../pages/SearchResults'
import UserProfile from '../pages/UserProfile'
import VideoDetails from '../pages/VideoDetails'
import UploadResource from '../pages/UploadResource'
import Notifications from '../pages/Notifications'
import Dashboard from '../pages/Dashboard'
import StudentProfile from '../pages/StudentProfile'
import EditProfile from '../pages/EditProfile'
import Login from '../pages/Login'
import Signup from '../pages/Signup'
import Onboarding from '../pages/Onboarding'
import { AuthProvider } from '../auth/AuthContext'
import { ProtectedRoute, PublicOnlyRoute } from '../auth/RouteGuards'

function AppRoutes() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
          <Route path="signup" element={<PublicOnlyRoute><Signup /></PublicOnlyRoute>} />
          <Route path="onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
          <Route element={<AppLayout />}>
            <Route index element={<Home />} />
            <Route path="home" element={<Home />} />
            <Route path="explore" element={<Explore />} />
            <Route path="resources/:slug/read" element={<PdfReader />} />
            <Route path="resources/:slug" element={<ResourceDetails />} />
            <Route path="videos/:slug" element={<VideoDetails />} />
            <Route path="search" element={<SearchResults />} />
            <Route path="saved" element={<ProtectedRoute><SavedResources /></ProtectedRoute>} />
            <Route path="community" element={<Community />} />
            <Route path="community/ask" element={<ProtectedRoute><AskQuestion /></ProtectedRoute>} />
            <Route path="questions/:slug" element={<QuestionDetails />} />
            <Route path="users/:username" element={<UserProfile />} />
            <Route path="pdf/:slug" element={<PdfReader />} />
            <Route path="upload" element={<ProtectedRoute><UploadResource /></ProtectedRoute>} />
            <Route path="notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
            <Route path="dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="profile" element={<ProtectedRoute><StudentProfile /></ProtectedRoute>} />
            <Route path="profile/edit" element={<ProtectedRoute><EditProfile /></ProtectedRoute>} />
            <Route path="profile/:username" element={<UserProfile />} />
            <Route path="community/questions/:slug" element={<QuestionDetails />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default AppRoutes
