import { cookies } from "next/headers"
import { NextResponse } from "next/server"

export async function POST(req: Request) {
  const formData = await req.formData()
  const password = String(formData.get("password") || "")

  if (password !== process.env.APP_PASSWORD) {
    return NextResponse.redirect(new URL("/login", req.url))
  }

  const cookieStore = await cookies()
  cookieStore.set("auth", "true", {
    httpOnly: true,
    path: "/",
  })

  return NextResponse.redirect(new URL("/", req.url))
}