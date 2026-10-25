import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { clearClientAuthState, getCurrentUser, login, logout, restoreSession, signup } from '../api/auth'
import { resetRefreshState, setAuthFailureHandler } from '../api/client'
import { AuthContext } from './context'
import { getLoginState } from './navigation'

function getAuthStatus(error) {
  return error?.status === 401 ? 'unauthenticated' : 'error'
}

export function AuthProvider({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading')
  const [initializationAttempt, setInitializationAttempt] = useState(0)
  const [initializationError, setInitializationError] = useState(null)
  const sessionInvalidated = useRef(false)

  useEffect(() => {
    const handleAuthFailure = () => {
      if (sessionInvalidated.current) return
      sessionInvalidated.current = true
      clearClientAuthState()
      resetRefreshState()
      setUser(null)
      setStatus('unauthenticated')
      setInitializationError(null)
      void logout().catch(() => {})
      if (location.pathname !== '/login' && location.pathname !== '/signup') {
        navigate('/login', { replace: true, state: getLoginState(location) })
      }
    }

    return setAuthFailureHandler(handleAuthFailure)
  }, [location, navigate])

  useEffect(() => {
    let active = true

    restoreSession()
      .then((nextUser) => {
        if (!active) return
        setUser(nextUser)
        setStatus(nextUser ? 'authenticated' : 'unauthenticated')
        setInitializationError(null)
      })
      .catch((error) => {
        if (!active) return
        setUser(null)
        setStatus(getAuthStatus(error))
        setInitializationError(error)
      })

    return () => {
      active = false
    }
  }, [initializationAttempt])

  const signIn = async (credentials) => {
    const result = await login(credentials)
    sessionInvalidated.current = false
    setUser(result.user)
    setStatus('authenticated')
    setInitializationError(null)
    return result
  }

  const signUp = (payload) => signup(payload)

  const refreshUser = async () => {
    try {
      const nextUser = await getCurrentUser()
      setUser(nextUser)
      setStatus('authenticated')
      setInitializationError(null)
      return nextUser
    } catch (error) {
      if (error?.status === 401) {
        clearClientAuthState()
        setUser(null)
        setStatus('unauthenticated')
        setInitializationError(null)
        return null
      }
      throw error
    }
  }

  const updateUser = (nextUser) => {
    setUser(nextUser)
    setStatus('authenticated')
    setInitializationError(null)
  }

  const signOut = async () => {
    try {
      await logout()
    } catch (error) {
      if (error?.status !== 401) throw error
    }

    setUser(null)
    sessionInvalidated.current = true
    setStatus('unauthenticated')
    setInitializationError(null)
  }

  const retryInitialization = () => {
    setStatus('loading')
    setInitializationError(null)
    setInitializationAttempt((attempt) => attempt + 1)
  }

  const value = {
    user,
    status,
    error: initializationError,
    signIn,
    signUp,
    refreshUser,
    updateUser,
    signOut,
    retryInitialization,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
