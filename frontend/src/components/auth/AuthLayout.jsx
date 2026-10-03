import AuthBrandPanel from './AuthBrandPanel'
import AuthHeader from './AuthHeader'

function AuthLayout({ children, variant }) {
  const isLogin = variant === 'login'
  return (
    <div className="min-h-svh bg-[var(--color-band)] text-[var(--color-text)]">
      <AuthHeader actionLabel={isLogin ? 'Sign Up' : 'Log In'} actionTo={isLogin ? '/signup' : '/login'} />
      <main className="grid min-h-[calc(100svh-4rem)] min-[900px]:grid-cols-[minmax(390px,39%)_1fr]">
        <AuthBrandPanel variant={variant} />
        <section className="flex items-center justify-center px-4 py-8 sm:px-8 sm:py-10 min-[900px]:px-10">
          {children}
        </section>
      </main>
    </div>
  )
}

export default AuthLayout
