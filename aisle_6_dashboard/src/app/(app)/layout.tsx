import ProtectedPage from "@/components/ProtectedPage"

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <ProtectedPage>{children}</ProtectedPage>
}