/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // The read-only demo builds into its own folder, so it can run beside the live console.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  async headers() {
    return [
      {
        source: "/media/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=86400, stale-while-revalidate=604800" },
        ],
      },
    ];
  },
  // Links shared before the website and dashboard became one app.
  async redirects() {
    return [
      { source: "/demo", destination: "/dashboard", permanent: true },
      { source: "/demo/:path*", destination: "/dashboard/:path*", permanent: true },
    ];
  },
};

export default nextConfig;
