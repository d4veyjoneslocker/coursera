import { NextRequest, NextResponse } from "next/server"

export function middleware(req: NextRequest) {
  const isLoggedIn = req.cookies.get("auth")?.value === "true"

  const isLoginPage = req.nextUrl.pathname === "/login"
  const isApi = req.nextUrl.pathname.startsWith("/api")
  const isStatic = req.nextUrl.pathname.startsWith("/_next")

  if (isLoginPage || isApi || isStatic) {
    return NextResponse.next()
  }

  if (!isLoggedIn) {
    return NextResponse.redirect(new URL("/login", req.url))
  }

  return NextResponse.next()
}