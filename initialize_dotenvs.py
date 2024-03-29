#!/usr/bin/env python
# This will create your initial .env files
# These are not to be checked in to git, as you may populate them
# with confidential information

# Standard Library
import os
import random
import string


def random_string(n):
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(n)
    )


CONFIG = [
    {
        "name": ".django",
        "sections": [
            {
                "name": "General",
                "envvars": [
                    ("USE_DOCKER", "yes"),
                    ("DJANGO_SECRET_KEY", lambda: random_string(20)),
                    ("IPYTHONDIR", "/app/.ipython"),
                ],
            },
            {
                "name": "Redis",
                "envvars": [("REDIS_URL", "redis://spotus_redis:6379/0")],
            },
            {
                "name": "Squarelet",
                "envvars": [("SQUARELET_KEY", ""), ("SQUARELET_SECRET", "")],
            },
        ],
    },
    {
        "name": ".postgres",
        "sections": [
            {
                "name": "PostgreSQL",
                "envvars": [
                    ("POSTGRES_HOST", "spotus_postgres"),
                    ("POSTGRES_PORT", "5432"),
                    ("POSTGRES_DB", "spotus"),
                    ("POSTGRES_USER", lambda: random_string(30)),
                    ("POSTGRES_PASSWORD", lambda: random_string(60)),
                ],
            }
        ],
    },
]


def main():
    os.makedirs(".envs/.local/", 0o775)
    for file_config in CONFIG:
        with open(".envs/.local/{}".format(file_config["name"]), "w") as file_:
            for section in file_config["sections"]:
                for key in ["name", "url", "description"]:
                    if key in section:
                        file_.write("# {}\n".format(section[key]))
                file_.write("# {}\n".format("-" * 78))
                for var, value in section["envvars"]:
                    file_.write(
                        "{}={}\n".format(var, value() if callable(value) else value)
                    )
                file_.write("\n")


if __name__ == "__main__":
    main()
