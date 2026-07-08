/** @type {import('next').NextConfig} */

// Packaged builds (Capacitor / Electron) need a static export served from
// local files — set BUILD_TARGET=static. The default (web/Vercel) keeps the
// API rewrite proxy and full SSR capability. Purely additive: web is unchanged.
const isStatic = process.env.BUILD_TARGET === "static";

const nextConfig = isStatic
  ? {
      reactStrictMode: true,
      output: "export",
      images: { unoptimized: true },
      // packaged shells load index.html per route directory
      trailingSlash: true,
    }
  : {
      reactStrictMode: true,
      async rewrites() {
        const backend = process.env.BACKEND_URL || "http://localhost:8000";
        return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
      },
    };

export default nextConfig;
