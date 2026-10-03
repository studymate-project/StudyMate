function GoogleAuthButton({ onClick }) {
  return <button type="button" onClick={onClick} className="flex min-h-11 w-full items-center justify-center gap-2 border-2 border-[var(--color-border-strong)] px-4 text-sm font-semibold text-white transition-colors hover:border-[var(--color-primary-light)] hover:bg-[var(--color-primary-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"><span className="text-xl font-bold leading-none" aria-hidden="true">G</span>Continue with Google</button>
}

export default GoogleAuthButton
