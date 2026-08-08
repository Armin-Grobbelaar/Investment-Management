/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    allowedDevOrigins: ['127.0.0.1', 'localhost'],
    // NOTE: the /api -> FastAPI proxy lives in src/middleware.ts, NOT here.
    // A next.config rewrite for '/api/:path*' also matched NextAuth's own
    // '/api/auth/*' routes and silently forwarded them to the backend
    // (e.g. GET /api/auth/csrf -> FastAPI 404), breaking sign-in. The
    // middleware proxy explicitly excludes /api/auth.
};

export default nextConfig;
