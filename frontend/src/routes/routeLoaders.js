const routeLoaders = {
  askQuestion: () => import('../pages/AskQuestion'),
  community: () => import('../pages/Community'),
  explore: () => import('../pages/Explore'),
  home: () => import('../pages/Home'),
  notFound: () => import('../pages/NotFound'),
  pdfReader: () => import('../pages/PdfReader'),
  questionDetails: () => import('../pages/QuestionDetails'),
  resourceDetails: () => import('../pages/ResourceDetails'),
  savedResources: () => import('../pages/SavedResources'),
  searchResults: () => import('../pages/SearchResults'),
  userProfile: () => import('../pages/UserProfile'),
  videoDetails: () => import('../pages/VideoDetails'),
  uploadResource: () => import('../pages/UploadResource'),
  notifications: () => import('../pages/Notifications'),
  dashboard: () => import('../pages/Dashboard'),
  studentProfile: () => import('../pages/StudentProfile'),
  editProfile: () => import('../pages/EditProfile'),
  login: () => import('../pages/Login'),
  signup: () => import('../pages/Signup'),
  onboarding: () => import('../pages/Onboarding'),
}

export function preloadRoute(routeKey) {
  const load = routeLoaders[routeKey]
  return load ? load() : Promise.resolve()
}

export default routeLoaders
