import { useQuery } from '@tanstack/react-query'
import { fetchResourceList } from '../api/resources'
import { QUERY_STALE_TIMES } from '../query/queryClient'
import { resourceKeys } from '../query/queryKeys'

export function useResourceList(params = {}) {
  const enabled = params !== null
  const query = enabled ? { ...params } : {}
  const result = useQuery({
    queryKey: resourceKeys.list(query),
    queryFn: () => fetchResourceList(query),
    enabled,
    staleTime: QUERY_STALE_TIMES.lists,
  })

  return {
    resources: result.data?.resources || [],
    pagination: result.data?.pagination || { count: 0, next: null, previous: null },
    loading: enabled && result.isPending,
    error: enabled ? result.error : null,
  }
}
