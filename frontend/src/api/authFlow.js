export function createLogoutCoordinator(logout) {
  let inFlight

  const request = () => {
    if (!inFlight) {
      inFlight = Promise.resolve()
        .then(logout)
        .finally(() => {
          inFlight = undefined
        })
    }
    return inFlight
  }

  const wait = () => inFlight || Promise.resolve()

  return { request, wait }
}

export function shouldAutoLogout({ status, user } = {}) {
  return status === 'authenticated' || Boolean(user)
}

export async function restoreSessionWithRefresh({ getCurrentUser, refreshSession }) {
  try {
    return await getCurrentUser()
  } catch (error) {
    if (error?.status !== 401) throw error

    try {
      await refreshSession()
    } catch (refreshError) {
      if (refreshError?.status === 401 || refreshError?.status === 429) return null
      throw refreshError
    }

    try {
      return await getCurrentUser()
    } catch (errorAfterRefresh) {
      if (errorAfterRefresh?.status === 401) return null
      throw errorAfterRefresh
    }
  }
}
