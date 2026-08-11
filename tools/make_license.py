"""厂商授权码签发工具。

用法:
    python tools/make_license.py --machine PX-ABCD-EF12-3456 --type duration --days 365 \
        --private-key /path/to/private_key.pem
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 SnapByFace 授权码")
    parser.add_argument("--machine", required=True, help="目标机器码")
    parser.add_argument("--days", type=int, default=365, help="时长授权天数")
    parser.add_argument("--credits", type=int, default=0, help="计数授权额度")
    parser.add_argument(
        "--type",
        choices=["count", "duration", "perpetual"],
        default="duration",
        help="授权类型",
    )
    parser.add_argument("--private-key", required=True, help="ECC 私钥 PEM 路径")
    args = parser.parse_args()

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from core.license import create_license

    key = create_license(
        machine_code=args.machine.strip(),
        license_type=args.type,
        days=args.days,
        credits=args.credits,
        private_key_path=args.private_key,
    )
    print(key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
