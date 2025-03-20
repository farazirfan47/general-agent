/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*', // Proxy API requests to FastAPI using IPv4
      },
      {
        source: '/ws/:path*',
        destination: 'http://127.0.0.1:8000/ws/:path*', // Proxy WebSocket connections using IPv4
      },
    ]
  },
}

module.exports = nextConfig 