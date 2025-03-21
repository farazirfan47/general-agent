/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Use environment variables with fallbacks
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    
    // For local development, use rewrites
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: `${apiUrl}/api/:path*`, // Use environment variable
        },
        {
          source: '/ws/:path*',
          destination: `${apiUrl}/ws/:path*`, // Keep using http for the proxy
        },
      ];
    }
    
    // For production, return empty array (no rewrites needed as we use absolute URLs)
    return [];
  },
}

module.exports = nextConfig 