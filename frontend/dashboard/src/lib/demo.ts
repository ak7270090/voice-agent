/**
 * The read-only demo build (NEXT_PUBLIC_DEMO_MODE=true): every read is answered from JSON
 * exported from real runs (exported into public/demo-data/), and
 * anything that would change data or place a call is refused with a clear message. No API,
 * runtime or LLM runs behind it, so it can be hosted for free.
 */

export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
export const READ_ONLY_STATUS = 403;
export const READ_ONLY_MESSAGE =
  "This is a demo workspace: changes and calls are turned off. Watch a call on the website.";
export const PROJECT_URL = process.env.NEXT_PUBLIC_PROJECT_URL ?? "";
export const REPOSITORY_URL = process.env.NEXT_PUBLIC_REPOSITORY_URL ?? "";

export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const DATA_ROOT = `${BASE_PATH}/demo-data`;
// Collections answered by filtering one exported list, as the API's query parameters do.
const CALL_FILTERS = ["agent_id", "channel", "direction", "outcome"];
const DEFAULT_CALL_LIMIT = 50;

type Row = Record<string, unknown>;

const loaded = new Map<string, Promise<unknown>>();

export class DemoNotFoundError extends Error {}

function load<T>(file: string): Promise<T> {
  if (!loaded.has(file)) {
    loaded.set(
      file,
      fetch(`${DATA_ROOT}/${file}.json`).then((response) => {
        if (!response.ok) throw new DemoNotFoundError(`not in the demo data: ${file}`);
        return response.json();
      }),
    );
  }
  return loaded.get(file) as Promise<T>;
}

async function findIn(file: string, id: string): Promise<Row> {
  const found = (await load<Row[]>(file)).find((row) => row.id === id);
  if (!found) throw new DemoNotFoundError(`not in the demo data: ${file}/${id}`);
  return found;
}

/** The demo's answer to a GET the console would send to the API. */
export async function demoGet(path: string): Promise<unknown> {
  const url = new URL(path, "http://demo");
  const parts = url.pathname.split("/").filter(Boolean);
  const [collection, id] = parts;
  if (collection === "calls" && parts.length === 1) {
    const filters = CALL_FILTERS.filter((key) => url.searchParams.get(key));
    const limit = Number(url.searchParams.get("limit") ?? DEFAULT_CALL_LIMIT);
    const calls = (await load<Row[]>("calls")).filter((call) =>
      filters.every((key) => call[key] === url.searchParams.get(key)),
    );
    return calls.slice(0, limit);
  }
  if (parts.length === 2 && ["calls", "agents", "campaigns"].includes(collection)) {
    return findIn(collection, id);
  }
  if (collection === "metrics") return load(`metrics-${url.searchParams.get("days") ?? 14}`);
  return load(parts.join("/"));
}

export const demoHealth = {
  status: "ok" as const,
  dependencies: { "read-only demo data": "ok" },
};
