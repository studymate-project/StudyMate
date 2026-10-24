import { useEffect, useState } from 'react'
import { listResources } from '../api/resources'

const initialState = {
  resources: [],
  pagination: { count: 0, next: null, previous: null },
  loading: true,
  error: null,
  queryKey: null,
}

export function useResourceList(params = {}) {
  const enabled = params !== null
  const queryKey = enabled ? JSON.stringify(params) : null
  const [state, setState] = useState(initialState)

  useEffect(() => {
    if (!enabled) {
      return undefined
    }

    let isCurrent = true

    listResources(JSON.parse(queryKey)).then(
      (result) => {
        if (isCurrent) setState({ ...result, loading: false, error: null, queryKey })
      },
      (error) => {
        if (isCurrent) setState({ ...initialState, loading: false, error, queryKey })
      },
    )

    return () => {
      isCurrent = false
    }
  }, [enabled, queryKey])

  const isCurrentQuery = state.queryKey === queryKey
  return {
    ...state,
    resources: isCurrentQuery ? state.resources : [],
    pagination: isCurrentQuery ? state.pagination : initialState.pagination,
    loading: !isCurrentQuery || state.loading,
    error: isCurrentQuery ? state.error : null,
  }
}
