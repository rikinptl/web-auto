import { NextRequest, NextResponse } from "next/server";

const COOKIE = "monitor_session";

export async function POST(request: NextRequest) {
  const password = process.env.MONITOR_PASSWORD;
  if (!password) {
    return NextResponse.json({ ok: true });
  }

  const body = (await request.json()) as { password?: string };
  if (body.password !== password) {
    return NextResponse.json({ error: "Invalid password" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE, password, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 14,
    path: "/",
  });
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.delete(COOKIE);
  return res;
}
