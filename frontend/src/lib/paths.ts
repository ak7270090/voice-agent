export const DASHBOARD_ROOT = "/dashboard";

/** Every link inside the app comes from here, so the app's address lives in one place. */
export function dashboardPath(path: string): string {
  return path === "/" ? DASHBOARD_ROOT : `${DASHBOARD_ROOT}${path}`;
}
