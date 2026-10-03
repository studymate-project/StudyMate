import Button from '../components/common/Button'

function NotFound() {
  return (
    <div className="mx-auto max-w-[900px] px-5 py-24 text-center">
      <h1 className="text-4xl font-black text-white">Page Not Found</h1>
      <p className="mt-4 font-black text-[var(--color-text)]">The page you opened does not exist in this StudyMate preview.</p>
      <Button to="/" className="mt-7">Go Home</Button>
    </div>
  )
}

export default NotFound
