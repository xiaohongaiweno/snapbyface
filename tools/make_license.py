"""厂商授权码签发工具。

用法:
    python tools/make_license.py --machine XXXX-XXXX-XXXX-XXXX --type month --days 30
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 SnapByFace 授权码")
    parser.add_argument("--machine", required=True, help="目标机器码")
    parser.add_argument("--days", type=int, required=True, help="授权天数")
    parser.add_argument("--type", default="custom", help="授权类型标签")
    args = parser.parse_args()

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from core.license import create_license

    key = create_license(
        machine_code=args.machine.strip(),
        license_type=args.type,
        days=args.days,
    )
    print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
