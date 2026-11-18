"""Create reference data and the first admin without demo accounts or sample requests."""

import argparse
import getpass

from .db import SessionLocal
from .models import Role, Unit, User
from .security import hash_password
from .seed import DEMO_PASSWORD, seed_reference


def bootstrap(email: str, password: str, name: str = "Administrator") -> bool:
    email = email.strip().lower()
    if "@" not in email or len(email) > 160:
        raise ValueError("Provide a valid admin email")
    if len(password) < 12 or password == DEMO_PASSWORD:
        raise ValueError("Use a unique admin password of at least 12 characters")
    with SessionLocal() as db:
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            if existing.role != Role.ADMIN:
                raise ValueError("The email already belongs to a non-admin user")
            return False
        if db.query(Unit).count() == 0:
            seed_reference(db)
        db.add(User(name=name.strip() or "Administrator", email=email,
                    password_hash=hash_password(password), role=Role.ADMIN))
        db.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()
    password = getpass.getpass("New admin password: ")
    if bootstrap(args.email, password, args.name):
        print("Admin created. No demo users or requests were added.")
    else:
        print("Admin already exists; no changes made.")


if __name__ == "__main__":
    main()
