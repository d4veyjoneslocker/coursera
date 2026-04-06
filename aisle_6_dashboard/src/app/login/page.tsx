export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-[#FAF7F1] px-6">
      <div className="w-full max-w-md rounded-2xl border border-[#E5DED3] bg-white p-8 shadow-sm">
        
        {/* Title */}
        <div className="mb-6">
          <p className="text-xs uppercase tracking-[0.18em] text-[#705C4F]">
            Aisle 6 Analytics Dashboard
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-[#343332]">
            Enter Password
          </h1>
        </div>

        {/* Form */}
        <form action="/api/login" method="POST">
          <input
            type="password"
            name="password"
            placeholder="Password"
            className="w-full rounded-xl border border-[#D8CFBF] px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-[#92B9DC]"
            required
          />

          <button
            type="submit"
            className="mt-4 w-full rounded-xl bg-[#343332] px-4 py-3 text-sm font-medium text-white transition hover:opacity-90"
          >
            Continue
          </button>
        </form>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-[#9A8F82]">
          Private dashboard
        </p>
      </div>
    </main>
  )
}