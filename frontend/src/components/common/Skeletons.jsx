export function Skeleton({ className = '' }) {
  return <span aria-hidden="true" className={`block animate-pulse rounded bg-[var(--color-surface-muted)] ${className}`} />
}

function SkeletonStatus({ label, className = '', children }) {
  return <div className={className} role="status" aria-label={label}>{children}</div>
}

export function ResourceCardSkeleton() {
  return <article className="min-h-[250px] rounded-lg border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5">
    <Skeleton className="h-14 w-14 rounded-lg" />
    <Skeleton className="mt-5 h-5 w-11/12" />
    <Skeleton className="mt-2 h-4 w-2/5" />
    <div className="mt-4 flex gap-2"><Skeleton className="h-4 w-24" /><Skeleton className="h-4 w-20" /></div>
    <div className="mt-4 flex gap-2"><Skeleton className="h-7 w-16 rounded-lg" /><Skeleton className="h-7 w-20 rounded-lg" /></div>
  </article>
}

export function ResourceGridSkeleton({ count = 4, horizontal = false }) {
  return <SkeletonStatus label="Loading resources" className={horizontal ? 'horizontal-scroll flex min-w-0 max-w-full gap-5 overflow-x-auto px-1 pb-4 pt-1' : 'col-span-full grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4'}>
    {Array.from({ length: count }, (_, index) => <div key={index} className={horizontal ? 'w-[min(82vw,300px)] shrink-0 sm:w-[280px] lg:w-[290px]' : ''}><ResourceCardSkeleton /></div>)}
  </SkeletonStatus>
}

export function ResourceListItemSkeleton() {
  return <article className="grid gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center">
    <div className="flex items-center gap-4"><Skeleton className="h-12 w-12 shrink-0 rounded-lg" /><div className="min-w-0"><Skeleton className="h-5 w-52 max-w-full" /><Skeleton className="mt-2 h-4 w-32" /></div></div>
    <div className="flex gap-4 sm:justify-end"><Skeleton className="h-4 w-24" /><Skeleton className="h-4 w-28" /></div>
    <Skeleton className="h-11 w-full rounded-xl sm:w-24" />
  </article>
}

export function ResourceListSkeleton({ count = 5 }) {
  return <SkeletonStatus label="Loading resources" className="space-y-3">{Array.from({ length: count }, (_, index) => <ResourceListItemSkeleton key={index} />)}</SkeletonStatus>
}

export function VideoCardSkeleton() {
  return <article className="flex w-full min-w-0 flex-col overflow-hidden rounded-xl bg-[var(--color-surface)]">
    <Skeleton className="aspect-video w-full rounded-none" />
    <div className="min-w-0 flex-1 p-3 sm:p-4"><Skeleton className="h-5 w-11/12" /><Skeleton className="mt-2 h-4 w-3/5" /></div>
  </article>
}

export function VideoGridSkeleton({ count = 6, horizontal = false }) {
  return <SkeletonStatus label="Loading videos" className={horizontal ? 'horizontal-scroll flex min-w-0 max-w-full gap-5 overflow-x-auto px-1 pb-4 pt-1' : 'mt-4 grid w-full min-w-0 grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3'}>
    {Array.from({ length: count }, (_, index) => <div key={index} className={horizontal ? 'w-[min(82vw,340px)] shrink-0 sm:w-[340px] lg:w-[360px]' : ''}><VideoCardSkeleton /></div>)}
  </SkeletonStatus>
}

export function QuestionCardSkeleton() {
  return <article className="grid gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:grid-cols-[80px_minmax(0,1fr)_80px]">
    <div className="border-r border-[var(--color-border)] pr-4"><Skeleton className="mx-auto h-7 w-12 sm:mx-0" /><Skeleton className="mx-auto mt-2 h-3 w-10 sm:mx-0" /></div>
    <div className="min-w-0"><Skeleton className="h-5 w-11/12" /><Skeleton className="mt-3 h-4 w-full" /><Skeleton className="mt-2 h-4 w-4/5" /><div className="mt-3 flex gap-2"><Skeleton className="h-7 w-16 rounded-lg" /><Skeleton className="h-7 w-20 rounded-lg" /></div><Skeleton className="mt-3 h-4 w-44" /></div>
    <div><Skeleton className="h-6 w-10" /><Skeleton className="mt-2 h-3 w-12" /></div>
  </article>
}

export function QuestionListSkeleton({ count = 5 }) {
  return <SkeletonStatus label="Loading questions" className="space-y-3">{Array.from({ length: count }, (_, index) => <QuestionCardSkeleton key={index} />)}</SkeletonStatus>
}

export function DiscussionGridSkeleton({ count = 3, horizontal = false }) {
  return <SkeletonStatus label="Loading discussions" className={horizontal ? 'horizontal-scroll flex min-w-0 max-w-full gap-5 overflow-x-auto px-1 pb-4 pt-1' : 'mt-6 grid grid-cols-1 gap-5 md:grid-cols-3'}>
    {Array.from({ length: count }, (_, index) => <article key={index} className={`${horizontal ? 'w-[min(82vw,340px)] shrink-0 sm:w-[340px] lg:w-[360px]' : ''} min-h-[210px] border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5`}><Skeleton className="h-10 w-10 rounded-lg" /><Skeleton className="mt-5 h-5 w-11/12" /><Skeleton className="mt-2 h-5 w-4/5" /><Skeleton className="mt-3 h-4 w-2/5" /><div className="mt-4 flex gap-5"><Skeleton className="h-4 w-8" /><Skeleton className="h-4 w-12" /></div></article>)}
  </SkeletonStatus>
}

export function ProfilePageSkeleton() {
  return <SkeletonStatus label="Loading profile">
    <section className="bg-[var(--color-band)] py-8"><div className="site-container"><div className="flex flex-col gap-5 sm:flex-row sm:items-start"><Skeleton className="h-16 w-16 shrink-0 rounded-full" /><div className="flex-1"><Skeleton className="h-7 w-48" /><Skeleton className="mt-2 h-4 w-40" /><Skeleton className="mt-3 h-4 w-64 max-w-full" /></div></div><div className="mt-7 grid grid-cols-2 gap-5 sm:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="flex flex-col items-center"><Skeleton className="h-6 w-12" /><Skeleton className="mt-2 h-3 w-20" /></div>)}</div></div></section>
    <main className="site-container min-h-[calc(100svh-26rem)] py-7"><Skeleton className="h-5 w-2/3" /><div className="mt-7 grid gap-7 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.9fr)]"><section><Skeleton className="h-4 w-24" /><div className="mt-3 space-y-3"><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /></div></section><aside className="space-y-6"><Skeleton className="h-24 w-full" /><Skeleton className="h-32 w-full" /></aside></div></main>
  </SkeletonStatus>
}

export function ProfileResourceListSkeleton({ count = 3 }) {
  return <SkeletonStatus label="Loading profile resources" className="space-y-3">
    {Array.from({ length: count }, (_, index) => <article key={index} className="flex flex-col gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0 flex-1"><Skeleton className="h-5 w-3/4" /><div className="mt-3 flex gap-2"><Skeleton className="h-5 w-20 rounded-lg" /><Skeleton className="h-5 w-24 rounded-lg" /></div><Skeleton className="mt-3 h-4 w-5/6" /></div><Skeleton className="h-9 w-20 rounded-lg" /></article>)}
  </SkeletonStatus>
}

export function ProfileQuestionListSkeleton({ count = 3 }) {
  return <SkeletonStatus label="Loading profile questions" className="space-y-3">
    {Array.from({ length: count }, (_, index) => <article key={index} className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4"><Skeleton className="h-5 w-11/12" /><div className="mt-3 flex gap-3"><Skeleton className="h-4 w-12" /><Skeleton className="h-4 w-20" /></div></article>)}
  </SkeletonStatus>
}

export function ProfileAnswerListSkeleton({ count = 3 }) {
  return <SkeletonStatus label="Loading profile answers" className="space-y-3">
    {Array.from({ length: count }, (_, index) => <article key={index} className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4"><Skeleton className="h-5 w-3/4" /><Skeleton className="mt-3 h-4 w-full" /><Skeleton className="mt-2 h-4 w-4/5" /></article>)}
  </SkeletonStatus>
}

export function PublicProfileSkeleton() {
  return <SkeletonStatus label="Loading profile" className="mx-auto w-full max-w-[1260px] px-5 py-8 sm:px-8 lg:px-10"><section className="p-6"><div className="flex flex-col gap-5 sm:flex-row sm:items-start"><Skeleton className="h-20 w-20 shrink-0 rounded-full" /><div className="flex-1"><Skeleton className="h-10 w-64 max-w-full" /><Skeleton className="mt-2 h-4 w-48" /><Skeleton className="mt-3 h-4 w-full max-w-2xl" /></div></div><div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <div key={index} className="bg-[var(--color-band)] p-4"><Skeleton className="mx-auto h-8 w-12" /><Skeleton className="mx-auto mt-2 h-4 w-24" /></div>)}</div></section><div className="mt-7 grid gap-7 lg:grid-cols-2"><div><Skeleton className="h-6 w-48" /><div className="mt-3 space-y-3"><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /></div></div><div><Skeleton className="h-6 w-40" /><div className="mt-3 space-y-3"><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /></div></div></div></SkeletonStatus>
}

export function ProfileFormSkeleton() {
  return <SkeletonStatus label="Loading profile" className="mx-auto w-full max-w-[900px] px-5 py-12 sm:px-8"><Skeleton className="h-9 w-52" /><div className="mt-7 space-y-5 rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-7">{Array.from({ length: 5 }, (_, index) => <div key={index}><Skeleton className="h-4 w-40" /><Skeleton className="mt-2 h-11 w-full rounded-lg" /></div>)}<div className="flex justify-end"><Skeleton className="h-11 w-32 rounded-xl" /></div></div></SkeletonStatus>
}

export function ResourceDetailSkeleton() {
  return <SkeletonStatus label="Loading resource" className="mx-auto w-full max-w-[1260px] px-5 py-6 sm:px-8 lg:px-10"><Skeleton className="h-4 w-80 max-w-full" /><div className="mt-5 grid gap-9 lg:grid-cols-[minmax(0,1fr)_330px]"><main><Skeleton className="h-40 w-full" /><Skeleton className="mt-6 h-28 w-full" /><Skeleton className="mt-6 h-[420px] w-full" /></main><aside className="space-y-6"><Skeleton className="h-40 w-full" /><Skeleton className="h-32 w-full" /></aside></div></SkeletonStatus>
}

export function QuestionDetailSkeleton() {
  return <SkeletonStatus label="Loading question" className="mx-auto w-full max-w-[1260px] px-5 py-6 sm:px-8 lg:px-10"><Skeleton className="h-4 w-72 max-w-full" /><div className="mt-5 grid gap-7 lg:grid-cols-[minmax(0,1fr)_310px]"><main><Skeleton className="h-48 w-full" /><Skeleton className="mt-7 h-24 w-full" /><Skeleton className="mt-7 h-52 w-full" /></main><aside><Skeleton className="h-48 w-full" /></aside></div></SkeletonStatus>
}

export function VideoDetailSkeleton() {
  return <SkeletonStatus label="Loading video" className="mx-auto w-full max-w-[1260px] px-5 py-6 sm:px-8 lg:px-10"><Skeleton className="h-4 w-72 max-w-full" /><div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_330px]"><main><Skeleton className="aspect-video w-full rounded-xl" /><Skeleton className="mt-7 h-32 w-full" /><Skeleton className="mt-6 h-44 w-full" /></main><aside><Skeleton className="h-40 w-full" /></aside></div></SkeletonStatus>
}

export function ReaderSkeleton() {
  return <SkeletonStatus label="Loading resource" className="mx-auto w-full max-w-[1100px] px-5 py-8 sm:px-8"><Skeleton className="h-4 w-36" /><Skeleton className="mt-4 h-9 w-2/3 max-w-full" /><Skeleton className="mt-6 min-h-[640px] w-full" /></SkeletonStatus>
}

export function DiscussionSkeleton() {
  return <SkeletonStatus label="Loading discussion" className="space-y-6 px-2 py-5">{Array.from({ length: 3 }, (_, index) => <div key={index} className="flex gap-3"><Skeleton className="h-9 w-9 shrink-0 rounded-full" /><div className="flex-1"><Skeleton className="h-4 w-40" /><Skeleton className="mt-2 h-4 w-full max-w-xl" /><Skeleton className="mt-2 h-4 w-2/3" /></div></div>)}</SkeletonStatus>
}

export function NotificationSkeleton() {
  return <SkeletonStatus label="Loading notifications" className="mx-auto w-full max-w-[1260px] px-5 py-7 sm:px-8 lg:px-10"><Skeleton className="h-8 w-48" /><Skeleton className="mt-2 h-4 w-72 max-w-full" /><div className="mt-7 space-y-2"><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" /></div></SkeletonStatus>
}

export function SearchResultsSkeleton() {
  return <SkeletonStatus label="Searching StudyMate" className="space-y-4"><Skeleton className="h-4 w-40" />{Array.from({ length: 5 }, (_, index) => <div key={index} className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5"><Skeleton className="h-4 w-24" /><Skeleton className="mt-3 h-5 w-3/4" /><Skeleton className="mt-2 h-4 w-full" /><Skeleton className="mt-2 h-4 w-2/3" /></div>)}</SkeletonStatus>
}

export function CatalogSkeleton({ rows = 3 }) {
  return <SkeletonStatus label="Loading options" className="selection-count grid gap-2">{Array.from({ length: rows }, (_, index) => <Skeleton key={index} className="h-10 w-full rounded-lg" />)}</SkeletonStatus>
}
