"""Opens every page of the read-only demo console and fails on a script error, a page that is
missing its data, or an action that does more than say the demo is read-only.

    console> NEXT_PUBLIC_DEMO_MODE=true NEXT_DIST_DIR=.next-demo npx next build
    console> NEXT_DIST_DIR=.next-demo npx next start -p 3100
    python tools/showcase/smoke_test.py [http://localhost:3100] [screenshot-folder]
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

DATA = Path(__file__).parents[2] / "console" / "public" / "demo-data"
READ_ONLY = "This is a demo workspace"
PAGE_TIMEOUT_MS = 20_000


def ids(file: str) -> list[str]:
    return [row["id"] for row in json.loads((DATA / f"{file}.json").read_text(encoding="utf-8"))]


def pages() -> list[tuple[str, str]]:
    """(path, text that shows the page loaded its data)."""
    agent = ids("agents")[0]
    return [
        ("/", "Calls per day"),
        ("/agents", "Appointment reminders"),
        (f"/agents/{agent}", "After the call"),
        (f"/agents/{agent}/flow", "Start"),
        ("/calls", "Analysis"),
        (f"/calls/{ids('calls')[0]}", "Sent after the call"),
        ("/campaigns", "Tomorrow's reminders"),
        (f"/campaigns/{ids('campaigns')[0]}", "Contacts"),
        ("/numbers", "Phone numbers"),
        ("/knowledge", "Knowledge"),
        (f"/knowledge/{ids('knowledge-bases')[0]}", "Documents"),
        ("/integrations", "Keys and tokens"),
    ]


def check(page: Page, base: str, shots: Path | None) -> list[str]:
    problems: list[str] = []
    page.on("pageerror", lambda error: problems.append(f"script error: {error}"))
    for path, marker in pages():
        page.goto(f"{base}{path}")
        try:
            page.get_by_text(marker).first.wait_for(timeout=PAGE_TIMEOUT_MS)
            page.get_by_text("Demo workspace").first.wait_for(timeout=PAGE_TIMEOUT_MS)
        except Exception:
            problems.append(f"{path}: '{marker}' or the demo banner never appeared")
        if page.get_by_text("not in the demo data").count():
            problems.append(f"{path}: data missing from the export")
        if shots:
            name = path.strip("/").split("/")[0] or "overview"
            page.screenshot(path=shots / f"demo-{name}.png")
    agent = ids("agents")[0]
    page.goto(f"{base}/agents/{agent}/flow")
    page.get_by_role("button", name="Start test call").click()
    try:
        page.get_by_text(READ_ONLY).first.wait_for(timeout=PAGE_TIMEOUT_MS)
    except Exception:
        problems.append("a test call did not say the demo is read-only")
    return problems


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"
    shots = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        problems = check(page, base, shots)
        browser.close()
    for problem in problems:
        print("FAIL", problem)
    print(f"{len(pages())} pages checked: {'PASSED' if not problems else 'FAILED'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
