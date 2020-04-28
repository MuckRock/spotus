# Third Party
from invoke import task

COMPOSE_PREFIX = "docker-compose -f local.yml"
COMPOSE_BUILD = f"COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 {COMPOSE_PREFIX} build {{opt}} {{service}}"
COMPOSE_RUN_OPT = f"{COMPOSE_PREFIX} run {{opt}} --rm {{service}} {{cmd}}"
COMPOSE_RUN_OPT_USER = COMPOSE_RUN_OPT.format(
    opt="-u $(id -u):$(id -g) {opt}", service="{service}", cmd="{cmd}"
)
COMPOSE_RUN = COMPOSE_RUN_OPT.format(opt="", service="{service}", cmd="{cmd}")
DJANGO_RUN = COMPOSE_RUN.format(service="spotus_django", cmd="{cmd}")
DJANGO_RUN_USER = COMPOSE_RUN_OPT_USER.format(
    opt="", service="spotus_django", cmd="{cmd}"
)


@task
def test(c, path="spotus", create_db=False, ipdb=False, slow=False):
    """Run the test suite"""
    create_switch = "--create-db" if create_db else ""
    ipdb_switch = "--pdb --pdbcls=IPython.terminal.debugger:Pdb" if ipdb else ""
    slow_switch = "" if slow else '-m "not slow"'

    c.run(
        COMPOSE_RUN_OPT_USER.format(
            opt="-e DJANGO_SETTINGS_MODULE=config.settings.test",
            service="spotus_django",
            cmd=f"pytest {create_switch} {ipdb_switch} {slow_switch} {path}",
        ),
        pty=True,
    )


@task
def testwatch(c, path="spotus"):
    """Run the test suite and watch for changes"""

    c.run(
        COMPOSE_RUN_OPT_USER.format(
            opt="-e DJANGO_SETTINGS_MODULE=config.settings.test",
            service="spotus_django",
            cmd=f"ptw {path}",
        ),
        pty=True,
    )


@task
def coverage(c):
    """Run the test suite with coverage report"""
    c.run(
        COMPOSE_RUN_OPT_USER.format(
            opt="-e DJANGO_SETTINGS_MODULE=config.settings.test",
            service="spotus_django",
            cmd=f"coverage erase",
        )
    )
    c.run(
        COMPOSE_RUN_OPT_USER.format(
            opt="-e DJANGO_SETTINGS_MODULE=config.settings.test",
            service="spotus_django",
            cmd=f"coverage run --source spotus -m py.test",
        )
    )
    c.run(
        COMPOSE_RUN_OPT_USER.format(
            opt="-e DJANGO_SETTINGS_MODULE=config.settings.test",
            service="spotus_django",
            cmd=f"coverage html",
        )
    )


@task
def pylint(c):
    """Run the linter"""
    c.run(DJANGO_RUN.format(cmd="pylint spotus"))


@task
def format(c):
    """Format your code"""
    c.run(
        DJANGO_RUN_USER.format(
            cmd="black spotus --exclude migrations && "
            "black config/urls.py && "
            "black config/api_router.py && "
            "black config/settings && "
            "isort -rc spotus && "
            "isort config/urls.py && "
            "isort config/api_router.py && "
            "isort -rc config/settings"
        )
    )


@task
def runserver(c):
    """Run the development server"""
    c.run(
        COMPOSE_RUN_OPT.format(
            opt="--service-ports --use-aliases", service="spotus_django", cmd=""
        )
    )


@task
def shell(c, opts=""):
    """Run an interactive python shell"""
    c.run(DJANGO_RUN.format(cmd=f"python manage.py shell_plus {opts}"), pty=True)


@task
def sh(c):
    """Run an interactive shell"""
    c.run(
        COMPOSE_RUN_OPT.format(opt="--use-aliases", service="spotus_django", cmd="sh"),
        pty=True,
    )


@task
def dbshell(c, opts=""):
    """Run an interactive db shell"""
    c.run(DJANGO_RUN.format(cmd=f"python manage.py dbshell {opts}"), pty=True)


@task
def celeryworker(c):
    """Run a celery worker"""
    c.run(
        COMPOSE_RUN_OPT.format(
            opt="--use-aliases", service="spotus_celeryworker", cmd=""
        )
    )


@task
def celerybeat(c):
    """Run the celery scheduler"""
    c.run(
        COMPOSE_RUN_OPT.format(opt="--use-aliases", service="spotus_celerybeat", cmd="")
    )


@task
def manage(c, cmd):
    """Run a Django management command"""
    c.run(DJANGO_RUN_USER.format(cmd=f"python manage.py {cmd}"), pty=True)


@task
def run(c, cmd):
    """Run a command directly on the docker instance"""
    c.run(DJANGO_RUN_USER.format(cmd=cmd))


@task(name="pip-compile")
def pip_compile(c, upgrade=False, package=None):
    """Run pip compile"""
    if package:
        upgrade_flag = f"--upgrade-package {package}"
    elif upgrade:
        upgrade_flag = "--upgrade"
    else:
        upgrade_flag = ""
    c.run(
        COMPOSE_RUN_OPT_USER.format(
            opt="-e PIP_TOOLS_CACHE_DIR=/tmp/pip-tools-cache",
            service="spotus_django",
            cmd=f"sh -c 'pip-compile {upgrade_flag} requirements/base.in && "
            f"pip-compile {upgrade_flag} requirements/local.in && "
            f"pip-compile {upgrade_flag} requirements/production.in'",
        )
    )


@task
def build(c, opt="", service=""):
    """Build the docker images"""
    c.run(COMPOSE_BUILD.format(opt=opt, service=service))


@task
def heroku(c, staging=False):
    """Run commands on heroku"""
    if staging:
        app = "spotus-staging"
    else:
        app = "spotus"
    c.run(f"heroku run --app {app} python manage.py shell_plus", pty=True)


@task
def up(c):
    """Start the docker images"""
    c.run("docker-compose -f local.yml up -d")
