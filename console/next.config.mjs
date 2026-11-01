/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // The read-only demo builds into its own folder, so it can run beside the live console.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
