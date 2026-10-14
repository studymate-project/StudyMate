function GoogleAuthButton({ onClick }) {
  return <button type="button" onClick={onClick} className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 text-sm font-semibold text-[var(--color-text)] transition-colors hover:border-[var(--color-focus)] hover:bg-[var(--color-blue-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]"><span className="text-xl font-bold leading-none" aria-hidden="true">G</span>Continue with Google</button>
}

export default GoogleAuthButton
