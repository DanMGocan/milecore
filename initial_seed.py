#!/usr/bin/env python3
"""Bootstrap the default MileCore demo company, site, and users."""

from backend.database import _lock, get_connection


DEFAULT_EMPLOYER = {
    "id": 1,
    "name": "Milestone",
    "type": "employer",
    "status": "active",
}

DEFAULT_SITE = {
    "id": 1,
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
        "id": 1,
        "name": "Dublin IT Support",
        "description": "Core IT support team for the seeded Dublin HQ site.",
        "team_type": "support",
    },
    {
        "id": 2,
        "name": "Dublin AV Support",
        "description": "AV support team for meeting rooms and event coverage at Dublin HQ.",
        "team_type": "av",
    },
]

DEFAULT_USERS = [
    {
        "id": 1,
        "first_name": "Dan",
        "last_name": "Gocan",
        "email": "dan.gocan@milestone.tech",
        "phone": "+353-1-555-1000",
        "role_title": "IT Technician",
        "department": "IT",
        "employer_id": 1,
        "site_id": 1,
        "team_id": 1,
        "team_role": "lead",
        "client_id": None,
        "vendor_id": None,
        "is_user": 1,
        "hire_date": "2021-02-01",
        "username": "dan",
        "user_role": "admin",
        "is_supervisor": 1,
        "status": "active",
    },
    {
        "id": 2,
        "first_name": "Bob",
        "last_name": "User",
        "email": "bob.user@milestone.tech",
        "phone": "+353-1-555-1006",
        "role_title": "AV Technician",
        "department": "AV",
        "employer_id": 1,
        "site_id": 1,
        "team_id": 2,
        "team_role": "member",
        "client_id": None,
        "vendor_id": None,
        "is_user": 1,
        "hire_date": "2022-05-16",
        "username": "bob",
        "user_role": "user",
        "is_supervisor": 0,
        "status": "active",
    },
]


def seed_initial_data() -> None:
    """Ensure the default demo company, site, home site, and users exist."""
    conn = get_connection()
    with _lock:
        conn.execute(
            """
            INSERT INTO companies (id, name, type, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                type = excluded.type,
                status = excluded.status
            """,
            [
                DEFAULT_EMPLOYER["id"],
                DEFAULT_EMPLOYER["name"],
                DEFAULT_EMPLOYER["type"],
                DEFAULT_EMPLOYER["status"],
            ],
        )
        conn.execute(
            """
            INSERT INTO sites (id, name, client_id, address, city, country, timezone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                client_id = excluded.client_id,
                address = excluded.address,
                city = excluded.city,
                country = excluded.country,
                timezone = excluded.timezone,
                status = excluded.status
            """,
            [
                DEFAULT_SITE["id"],
                DEFAULT_SITE["name"],
                DEFAULT_SITE["client_id"],
                DEFAULT_SITE["address"],
                DEFAULT_SITE["city"],
                DEFAULT_SITE["country"],
                DEFAULT_SITE["timezone"],
                DEFAULT_SITE["status"],
            ],
        )
        conn.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES ('home_site_id', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            [str(DEFAULT_SITE["id"])],
        )

        for team in DEFAULT_TEAMS:
            conn.execute(
                """
                INSERT INTO teams (id, name, description, team_type)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    team_type = excluded.team_type
                """,
                [
                    team["id"],
                    team["name"],
                    team["description"],
                    team["team_type"],
                ],
            )

        for user in DEFAULT_USERS:
            conn.execute(
                """
                INSERT INTO people (
                    id, first_name, last_name, email, phone, role_title, department,
                    site_id, team_id, team_role, employer_id, client_id, vendor_id,
                    is_supervisor, hire_date, is_user, username, user_role, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    email = excluded.email,
                    phone = excluded.phone,
                    role_title = excluded.role_title,
                    department = excluded.department,
                    team_id = excluded.team_id,
                    team_role = excluded.team_role,
                    employer_id = excluded.employer_id,
                    client_id = excluded.client_id,
                    vendor_id = excluded.vendor_id,
                    site_id = excluded.site_id,
                    is_supervisor = excluded.is_supervisor,
                    hire_date = excluded.hire_date,
                    is_user = excluded.is_user,
                    username = excluded.username,
                    user_role = excluded.user_role,
                    status = excluded.status
                """,
                [
                    user["id"],
                    user["first_name"],
                    user["last_name"],
                    user["email"],
                    user["phone"],
                    user["role_title"],
                    user["department"],
                    user["site_id"],
                    user["team_id"],
                    user["team_role"],
                    user["employer_id"],
                    user["client_id"],
                    user["vendor_id"],
                    user["is_supervisor"],
                    user["hire_date"],
                    user["is_user"],
                    user["username"],
                    user["user_role"],
                    user["status"],
                ],
            )

        conn.commit()


def main() -> None:
    seed_initial_data()
    print("Initial seed applied.")


if __name__ == "__main__":
    main()
