#!/usr/bin/env python3
"""
Utility script to bootstrap a Tryton user and group for the web portal.

Usage (from repo root):
    docker compose run --rm tryton python3 tryton/scripts/setup_portal_group.py

Environment variables:
    TRYTON_DATABASE  - database name (default: tryton)
    TRYTON_CONFIG    - path to trytond.conf (default: /etc/tryton/trytond.conf)
    PORTAL_LOGIN     - login to create/update (default: portal.client)
    PORTAL_PASSWORD  - password to set (default: Motdepasse!123)
    PORTAL_GROUP     - group descriptive name (default: Portail Clients)
"""

from __future__ import annotations

import os

from trytond.config import config
from trytond.pool import Pool
from trytond.transaction import Transaction


def ensure_group(pool: Pool, name: str):
    Group = pool.get("res.group")
    groups = Group.search([("name", "=", name)], limit=1)
    if groups:
        return groups[0], False
    group, = Group.create([{"name": name}])
    return group, True


def ensure_user(pool: Pool, login: str, password: str):
    User = pool.get("res.user")
    users = User.search([("login", "=", login)], limit=1)
    if users:
        user = users[0]
        User.write([user], {"password": password, "active": True})
        return user, False
    user, = User.create(
        [
            {
                "name": login,
                "login": login,
                "password": password,
                "active": True,
            }
        ]
    )
    return user, True


def main():
    db_name = os.environ.get("TRYTON_DATABASE", "tryton")
    conf_path = os.environ.get("TRYTON_CONFIG", "/etc/tryton/trytond.conf")
    portal_login = os.environ.get("PORTAL_LOGIN", "portal.client")
    portal_password = os.environ.get("PORTAL_PASSWORD", "Motdepasse!123")
    portal_group_name = os.environ.get("PORTAL_GROUP", "Portail Clients")

    config.update_etc(conf_path)
    Pool(db_name).init()
    pool = Pool(db_name)

    with Transaction().start(db_name, 0, context={}) as transaction:
        group, group_created = ensure_group(pool, portal_group_name)
        user, user_created = ensure_user(pool, portal_login, portal_password)

        User = pool.get("res.user")
        user_record = User.browse([user.id])[0]
        existing_group_ids = [grp.id for grp in user_record.groups]
        updates = []
        if existing_group_ids:
            updates.append(("remove", existing_group_ids))
        updates.append(("add", [group.id]))
        User.write([user_record], {"groups": updates})

        transaction.commit()

    if group_created:
        print(f"Created group '{portal_group_name}'.")
    else:
        print(f"Group '{portal_group_name}' already exists.")

    if user_created:
        print(f"Created user '{portal_login}'.")
    else:
        print(f"Updated user '{portal_login}'.")

    print(f"Assigned user '{portal_login}' to group '{portal_group_name}'.")


if __name__ == "__main__":
    main()
