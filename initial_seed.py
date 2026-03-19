#!/usr/bin/env python3
"""Bootstrap the default TrueCore.cloud demo company, site, and users."""

import json
import os

from backend.database import execute_query


DEFAULT_EMPLOYER = {
    "name": "Milestone",
    "type": "employer",
    "status": "active",
}

DEFAULT_SITE = {
    "name": "Dublin HQ",
    "client_id": None,
    "address": "45 Grand Canal Dock, Dublin 2",
    "city": "Dublin",
    "country": "Ireland",
    "timezone": "Europe/Dublin",
    "status": "active",
}

DEFAULT_TEAMS = [
    {
        "name": "Dublin IT Support",
        "description": "Core IT support team for the seeded Dublin HQ site.",
        "team_type": "support",
    },
    {
        "name": "Dublin AV Support",
        "description": "AV support team for meeting rooms and event coverage at Dublin HQ.",
        "team_type": "av",
    },
]

DEFAULT_USERS = [
    {
        "first_name": "Dan",
        "last_name": "Gocan",
        "email": "dan.gocan@milestone.tech",
        "phone": "+353-1-555-1000",
        "role_title": "IT Technician",
        "department": "IT",
        "team_idx": 0,
        "team_role": "lead",
        "is_user": 1,
        "hire_date": "2021-02-01",
        "username": "dan",
        "user_role": "owner",
        "is_supervisor": 1,
        "status": "active",
    },
    {
        "first_name": "Bob",
        "last_name": "User",
        "email": "bob.user@milestone.tech",
        "phone": "+353-1-555-1006",
        "role_title": "AV Technician",
        "department": "AV",
        "team_idx": 1,
        "team_role": "member",
        "is_user": 1,
        "hire_date": "2022-05-16",
        "username": "bob",
        "user_role": "user",
        "is_supervisor": 0,
        "status": "active",
    },
]


def seed_initial_data(instance_id: int = 1) -> None:
    """Ensure the default demo company, site, home site, and users exist for an instance."""

    # Insert employer
    emp = execute_query(
        "INSERT INTO companies (name, type, status, instance_id) VALUES (?, ?, ?, ?) "
        "ON CONFLICT DO NOTHING RETURNING id",
        [DEFAULT_EMPLOYER["name"], DEFAULT_EMPLOYER["type"], DEFAULT_EMPLOYER["status"], instance_id],
        instance_id=instance_id,
    )
    # If ON CONFLICT hit, look it up
    if emp.get("lastrowid"):
        employer_id = emp["lastrowid"]
    else:
        r = execute_query(
            "SELECT id FROM companies WHERE name = ? AND instance_id = ?",
            [DEFAULT_EMPLOYER["name"], instance_id],
            instance_id=instance_id,
        )
        employer_id = r["rows"][0]["id"] if r.get("rows") else None

    # Insert site
    site = execute_query(
        "INSERT INTO sites (name, client_id, address, city, country, timezone, status, instance_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING RETURNING id",
        [
            DEFAULT_SITE["name"], DEFAULT_SITE["client_id"], DEFAULT_SITE["address"],
            DEFAULT_SITE["city"], DEFAULT_SITE["country"], DEFAULT_SITE["timezone"],
            DEFAULT_SITE["status"], instance_id,
        ],
        instance_id=instance_id,
    )
    if site.get("lastrowid"):
        site_id = site["lastrowid"]
    else:
        r = execute_query(
            "SELECT id FROM sites WHERE name = ? AND instance_id = ?",
            [DEFAULT_SITE["name"], instance_id],
            instance_id=instance_id,
        )
        site_id = r["rows"][0]["id"] if r.get("rows") else None

    # Set home site
    execute_query(
        "INSERT INTO app_settings (instance_id, key, value) VALUES (?, 'home_site_id', ?) "
        "ON CONFLICT (instance_id, key) DO UPDATE SET value = excluded.value",
        [instance_id, str(site_id)],
        instance_id=instance_id,
    )

    # Last push timestamp
    last_push_path = os.path.join(os.path.dirname(__file__), "last_push.json")
    try:
        with open(last_push_path) as f:
            push_ts = json.load(f).get("timestamp")
    except (FileNotFoundError, json.JSONDecodeError):
        push_ts = None

    if push_ts:
        execute_query(
            "INSERT INTO app_settings (instance_id, key, value) VALUES (?, 'last_push_at', ?) "
            "ON CONFLICT (instance_id, key) DO UPDATE SET value = excluded.value",
            [instance_id, push_ts],
            instance_id=instance_id,
        )

    # Insert teams
    team_ids = []
    for team in DEFAULT_TEAMS:
        t = execute_query(
            "INSERT INTO teams (name, description, team_type, instance_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT DO NOTHING RETURNING id",
            [team["name"], team["description"], team["team_type"], instance_id],
            instance_id=instance_id,
        )
        if t.get("lastrowid"):
            team_ids.append(t["lastrowid"])
        else:
            r = execute_query(
                "SELECT id FROM teams WHERE name = ? AND instance_id = ?",
                [team["name"], instance_id],
                instance_id=instance_id,
            )
            team_ids.append(r["rows"][0]["id"] if r.get("rows") else None)

    # Insert users
    for user in DEFAULT_USERS:
        team_id = team_ids[user["team_idx"]] if user["team_idx"] < len(team_ids) else None
        execute_query(
            """
            INSERT INTO people (
                first_name, last_name, email, phone, role_title, department,
                site_id, team_id, team_role, employer_id,
                is_supervisor, hire_date, is_user, username, user_role, status, instance_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT DO NOTHING
            """,
            [
                user["first_name"], user["last_name"], user["email"], user["phone"],
                user["role_title"], user["department"],
                site_id, team_id, user["team_role"], employer_id,
                user["is_supervisor"], user["hire_date"],
                user["is_user"], user["username"], user["user_role"], user["status"],
                instance_id,
            ],
            instance_id=instance_id,
        )


def main() -> None:
    seed_initial_data()
    print("Initial seed applied.")


if __name__ == "__main__":
    main()
