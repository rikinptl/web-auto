import { NextRequest, NextResponse } from "next/server";

const COOKIE = "monitor_session";

export function middleware(request: NextRequest) {
  const password = process.env.MONITOR_PASSWORD;
  if (!password) return NextResponse.next();

  const { pathname } = request.nextUrl;
  if (pathname.startsWith("/login") || pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }

  const session = request.cookies.get(COOKIE)?.value;
  if (session === password) return NextResponse.next();

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const login = new URL("/login", request.url);
  login.searchParams.set("from", pathname);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
