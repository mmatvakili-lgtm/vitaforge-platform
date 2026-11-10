import { NextResponse, type NextRequest } from "next/server";

const LOCALES = ["fa", "en"];

function preferred(req: NextRequest): string {
  const cookie = req.cookies.get("vf_locale")?.value;
  if (cookie && LOCALES.includes(cookie)) return cookie;
  const al = req.headers.get("accept-language")?.toLowerCase() ?? "";
  return al.startsWith("en") ? "en" : "fa";
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (LOCALES.some((l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`))) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = `/${preferred(req)}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(url);
}

export const config = { matcher: ["/((?!api|_next|favicon.ico|.*\\..*).*)"] };
