import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Proxies frontend `/api/*` calls to the FastAPI backend, mirroring the
 * behaviour of the old next.config rewrite — EXCEPT NextAuth's own
 * `/api/auth/*` routes, which must be handled by the Next.js route handler.
 *
 * The old rewrite (`source: '/api/:path*'`) matched `/api/auth/*` too and
 * forwarded it to the backend, which returned 404 — breaking sign-in.
 */
const BACKEND_ORIGIN = 'http://127.0.0.1:3337';

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // NextAuth routes are handled by the Next.js route handler, not the backend.
    if (pathname === '/api/auth' || pathname.startsWith('/api/auth/')) {
        return NextResponse.next();
    }

    // Everything else under /api is proxied to the FastAPI backend
    // (the /api prefix is stripped, matching the backend's root-level routes).
    const url = request.nextUrl.clone();
    url.protocol = 'http';
    url.host = '127.0.0.1';
    url.port = '3337';
    url.pathname = pathname.replace(/^\/api/, '') || '/';
    return NextResponse.rewrite(url);
}

export const config = {
    matcher: ['/api/:path*'],
};
