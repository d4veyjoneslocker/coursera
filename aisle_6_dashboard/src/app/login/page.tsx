export default function LoginPage() {
  return (
    <form action="/api/login" method="POST" className="p-10">
      <h1>Enter Password</h1>
      <input
        type="password"
        name="password"
        className="border p-2 mt-2"
        required
      />
      <button className="block mt-4 bg-black text-white px-4 py-2">
        Submit
      </button>
    </form>
  )
}