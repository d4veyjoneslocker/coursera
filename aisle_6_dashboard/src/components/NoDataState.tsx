// components/NoDataState.tsx
export default function NoDataState() {
  return (
    <div className="p-6">
      <div
        className="rounded-2xl border p-10 text-center"
        style={{
          borderColor: "#E5DDD0",
          backgroundColor: "#F8F4EC",
        }}
      >
        <h2
          className="text-lg font-semibold mb-2"
          style={{ color: "#343332" }}
        >
          No data yet
        </h2>

        <p
          className="text-sm"
          style={{ color: "#7A746B" }}
        >
          Upload your KeHE report to start building your dashboard.
        </p>
      </div>
    </div>
  )
}