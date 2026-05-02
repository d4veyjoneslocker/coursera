import ProtectedPage from "@/components/ProtectedPage"

export const dynamic = "force-dynamic"


export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  console.log("APP LAYOUT RUNNING")

  return <ProtectedPage>{children}</ProtectedPage>
}