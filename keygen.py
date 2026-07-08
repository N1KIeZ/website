"""License key generator — generates keys server-side via the admin API."""
import argparse
import json
import os
import urllib.request
import urllib.error

API_BASE = os.environ.get("API_BASE", "https://website-0bcg.onrender.com")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")


def main():
    parser = argparse.ArgumentParser(description="Generate license keys")
    parser.add_argument("amount", nargs="?", type=int, default=10, help="Number of keys to generate (default: 10)")
    parser.add_argument("--admin-key", default=ADMIN_KEY, help="Admin API key (or set ADMIN_KEY env var)")
    parser.add_argument("--api", default=API_BASE, help=f"API base URL (default: {API_BASE})")
    parser.add_argument("--output", "-o", help="Save keys to file (printed to stdout otherwise)")
    args = parser.parse_args()

    if not args.admin_key:
        print("ERROR: Admin key required. Set ADMIN_KEY env var or pass --admin-key")
        return

    url = f"{args.api.rstrip('/')}/api/generate"
    body = json.dumps({"amount": args.amount}).encode()

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {args.admin_key}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR {e.code}: {e.read().decode()}")
        return
    except urllib.error.URLError as e:
        print(f"ERROR: {e.reason}")
        return

    keys = [k["key"] for k in data]

    if args.output:
        with open(args.output, "w") as f:
            for k in keys:
                f.write(k + "\n")
        print(f"Saved {len(keys)} keys to {args.output}")
    else:
        print(f"Generated {len(keys)} keys:\n")
        for k in keys:
            print(k)


if __name__ == "__main__":
    main()
