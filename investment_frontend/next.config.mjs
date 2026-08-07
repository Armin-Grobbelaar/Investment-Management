/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    allowedDevOrigins: ['127.0.0.1', 'localhost'],
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://127.0.0.1:3337/:path*',
            },
        ];
    },
};

export default nextConfig;
