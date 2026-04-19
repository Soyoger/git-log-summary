import json
import sys
from argparse import ArgumentParser
import urllib.error
import urllib.request

DEFAULT_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxx"


def main() -> int:
    parser = ArgumentParser(add_help=True)
    parser.add_argument(
        "text",
        nargs="?",
        default="测试",
        help='Text message to send (default: "测试")',
    )
    args = parser.parse_args()

    payload = {
        "msg_type": "text",
        "content": {"text": args.text},
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        DEFAULT_WEBHOOK,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(body)
            return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        print(body, file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())