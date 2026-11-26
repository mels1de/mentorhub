"""Usage: python -m app.modules.users.cli create-admin EMAIL (the password is prompted for)."""

import argparse
import asyncio
import getpass
import sys

from pydantic import TypeAdapter, ValidationError
from pydantic.networks import EmailStr

from app.core.config import get_settings
from app.db.session import create_engine, create_session_factory
from app.modules.auth.schemas import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from app.modules.users.models import UserRole
from app.modules.users.service import UserService


async def create_admin(email: str, password: str) -> None:
    engine = create_engine(get_settings())
    try:
        async with create_session_factory(engine)() as session:
            user = await UserService(session).create(
                email=email, password=password, role=UserRole.ADMIN
            )
            user.is_email_verified = True
            await session.commit()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="users")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create-admin").add_argument("email")
    args = parser.parse_args()

    try:
        email = TypeAdapter(EmailStr).validate_python(args.email)
    except ValidationError:
        sys.exit("Invalid email.")
    password = getpass.getpass("Password: ")
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        sys.exit(f"Password must be {MIN_PASSWORD_LENGTH}-{MAX_PASSWORD_LENGTH} characters.")
    if getpass.getpass("Repeat password: ") != password:
        sys.exit("Passwords do not match.")

    asyncio.run(create_admin(email, password))
    print(f"Admin {email} created.")


if __name__ == "__main__":
    main()
