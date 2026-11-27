# /// script
# dependencies = ["websocket-client"]
# ///
"""Evaluate JavaScript in a tab of the nested Chrome over CDP.

    uv run cdp_eval.py --port PORT --url portal.example.com 'document.title'
    uv run cdp_eval.py --port PORT --file fetch_items.js > items.json

PORT is the CDP port `nested_chrome.py start` (or `status`) prints. It differs
on every start; never guess it, another browser may own the port you guess.

The expression may return a promise (it is awaited); the value comes back
as JSON, or raw if it is a string. Runs in the page, so fetch() carries the
page's cookies: read a site's own JSON endpoints instead of scraping HTML.
"""

import argparse
import json
import sys
import urllib.request

import websocket


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, required=True, help="CDP port printed by nested_chrome.py start")
    ap.add_argument("--url", default="", help="pick the first tab whose URL contains this")
    ap.add_argument("--file", help="read the expression from this file")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("expr", nargs="?")
    args = ap.parse_args()
    expr = open(args.file).read() if args.file else args.expr
    if not expr:
        ap.error("give an expression or --file")

    tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{args.port}/json/list"))
    tabs = [t for t in tabs if t["type"] == "page" and args.url in t["url"]]
    if not tabs:
        sys.exit(f"no tab with {args.url!r} in its URL")
    ws = websocket.create_connection(tabs[0]["webSocketDebuggerUrl"], timeout=args.timeout, suppress_origin=True)
    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                        "params": {"expression": expr, "awaitPromise": True, "returnByValue": True}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == 1:
            break
    if "error" in msg:  # a protocol error, e.g. the page navigated away mid-evaluation
        sys.exit("CDP error: " + json.dumps(msg["error"])[:2000])
    res = msg["result"]
    if "exceptionDetails" in res:
        sys.exit("exception: " + json.dumps(res["exceptionDetails"])[:2000])
    value = res["result"].get("value")
    print(value if isinstance(value, str) else json.dumps(value))


if __name__ == "__main__":
    main()
