/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // The read-only demo builds into its own folder, so it can run beside the live console.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // The hosted demo lives under /demo on the website's address; locally this is empty.
  basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? "",
};

export default nextConfig;
