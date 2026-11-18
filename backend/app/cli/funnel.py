"""Print the product funnel: python -m app.cli.funnel [--days 30]

Reads only aggregate counts of distinct people; prints no identifiers or personal data.
"""

import argparse

from app.db.session import SessionLocal
from app.services.funnel import funnel_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, help="Sign-up window in days")
    args = parser.parse_args()
    with SessionLocal() as db:
        report = funnel_report(db, days=args.days)
    top = report[0][1] or 1
    print(f"CareerOS funnel, people who signed up in the last {args.days} days")
    for label, count in report:
        print(f"  {label:<26} {count:>6}  {round(100 * count / top):>3}%")


if __name__ == "__main__":
    main()
