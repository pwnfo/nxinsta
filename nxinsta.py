from rich.console import Console
from rich.theme import Theme
from rich.logging import RichHandler
from rich.text import Text
from rich.prompt import Prompt
from rich.markup import render
from rich.status import Status
from rich.table import Table
from rich import box
from instagrapi import Client
from instagrapi.exceptions import PrivateError

import time
import argparse
import logging
import sys
import os
from typing import Any

DEFAULT_SESSION_FILE = ".nxinsta_session.json"

__author__ = "Ryan R. <pwnfo@proton.me>"
__version__ = "0.1.0"

nx_theme = Theme(
    {
        "nx.purple": "#833AB4",
        "nx.pink": "#E1306C",
        "nx.red": "#F56040",
        "nx.orange": "#F77737",
        "nx.yellow": "#FCAF45",
        "success": "#E1306C",
        "warning": "#F77737",
        "danger": "#F56040",
        "info": "#833AB4",
        "accent": "bold #FCAF45",
        "text.muted": "#777777",
    }
)

console = Console(theme=nx_theme)
cl = Client()


class PlainRichHandler(RichHandler):
    def render_message(self, record: logging.LogRecord, message: str) -> Text:
        return render(message)

    def get_level_text(self, record: logging.LogRecord) -> Text:
        return Text(record.levelname)


class NxRichHandler(PlainRichHandler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.WARNING:
            self.console = Console(file=sys.stdout, theme=nx_theme)
        else:
            self.console = Console(file=sys.stderr, theme=nx_theme)

        super().emit(record)


class NxFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.WARNING:
            return f"[bold yellow]\\[WARN][/bold yellow] {record.getMessage()}"
        if record.levelno == logging.ERROR:
            return f"[bold red]\\[ERROR][/bold red] {record.getMessage()}"
        return record.getMessage()


def setup_logger(name: str = "nxinsta") -> logging.Logger:
    log = logging.getLogger(name)

    handler = NxRichHandler(
        markup=True,
        rich_tracebacks=True,
        show_time=False,
        show_level=False,
        show_path=False,
        keywords=[],
    )

    handler.setFormatter(NxFormatter())

    log.setLevel(logging.INFO)
    if not any(isinstance(h, NxRichHandler) for h in log.handlers):
        log.addHandler(handler)
    log.propagate = False

    logging.getLogger("instagrapi").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    return log


log = setup_logger()


class DotLoader:
    def __init__(self, message: str, spinner: str = "dots") -> None:
        self.message = message
        self.spinner = spinner
        self._status: Status | None = None

    def set_message(self, message: str) -> None:
        self.message = message
        if self._status is not None:
            self._status.update(message)

    def __enter__(self) -> "DotLoader":
        self._status = console.status(
            self.message, spinner=self.spinner, spinner_style="info"
        )
        self._status.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._status is not None:
            self._status.__exit__(exc_type, exc, tb)
            self._status = None


def print_banner() -> None:
    banner = [
        r" _  ___  _____ _  _ ___ _____ _   ",
        r"| \| \ \/ /_ _| \| / __|_   _/_\  ",
        r"| .` |>  < | || .` \__ \ | |/ _ \ ",
        r"|_|\_/_/\_\___|_|\_|___/ |_/_/ \_\ ",
        f"                                   v{__version__}",
    ]

    g = ["#2A0845", "#4B0F6B", "#6A1B9A", "#833AB4", "#6A1B9A"]

    for line, color in zip(banner, g):
        text = Text(" " + line, style=color)
        console.print(text)
    console.print("\n")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nxinsta",
        add_help=False,
        usage=f"nxinsta [options] @target",
        description="Infer private social connections on Instagram\nusing recommendation analysis.",
        epilog=f"Developed by: {__author__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    a = parser.add_argument_group("Options")

    # fmt: off
    a.add_argument("-h", "--help", action="help", help="display this help message")
    a.add_argument("-v", "--version", action="version", version=f"NxInsta v{__version__}", help="show version",)

    a.add_argument("-m", "--max", type=int, metavar="<max>", default=24, help="max accounts to enumerate (default: 24)",)
    a.add_argument("-l", "--login", metavar="<user:pass>", dest="login", help="login with credentials",)
    a.add_argument("-s", "--session", metavar="<path>", dest="session", help="path to session file", default=DEFAULT_SESSION_FILE,)
    a.add_argument("-o", "--output", metavar="<path>", dest="output", help="save results to a file",)

    parser.add_argument("target", metavar="@target", help=argparse.SUPPRESS)
    # fmt: on

    return parser


def login(credentials: tuple[str, str] | None = None) -> None:
    username = None
    password = None
    save = None

    if credentials is None:
        log.info(
            "Log in with your [nx.pink]Instagram[/] credentials to continue.\n[bold][nx.yellow]Note:[/][/] It is recommended to use an alternate account.\n"
        )
    else:
        log.info("Logging into your [nx.pink]Instagram[/] account...")

    if credentials is None:
        while 1:
            username = Prompt.ask("Username")
            if username == "":
                console.print("[danger][bold]Username cannot be empty.[/][/]\n")
            else:
                break
        while 1:
            password = Prompt.ask("Password", password=True)
            if password == "":
                console.print("[danger][bold]Password cannot be empty.[/][/]\n")
            else:
                break
    else:
        username = credentials[0]
        password = credentials[1]

    console.line()

    try:
        with DotLoader("Authenticating...", spinner="dots"):
            cl.login(username, password)
    except Exception as e:
        log.error(e)
        sys.exit(1)

    log.info(f"[green]Login successful.[/]\n")
    console.print(
        f"Do you want to save the session file as a [accent]{DEFAULT_SESSION_FILE}[/]\nfile for the next time you run the command?\n"
    )

    while 1:
        save = console.input("[accent][y/n][/] Save session? ").lower()

        if save not in ("y", "yes", "n", "no"):
            console.print(
                '[danger][bold]Please choose between Y ("yes") or N ("no").[/][/]\n'
            )
        else:
            break

    if save in ("y", "yes"):
        cl.dump_settings(DEFAULT_SESSION_FILE)


def _extract_user_fields(user: Any) -> tuple[str | int | None, str | None, bool]:
    if isinstance(user, dict):
        return (
            user.get("pk"),
            user.get("username"),
            user.get("is_private", False),
        )

    return (
        getattr(user, "pk", None),
        getattr(user, "username", None),
        getattr(user, "is_private", False),
    )


def _extract_user_name(user: Any) -> str:
    if isinstance(user, dict):
        return user.get("full_name") or user.get("name") or user.get("username") or "-"

    return (
        getattr(user, "full_name", None)
        or getattr(user, "name", None)
        or getattr(user, "username", None)
        or "-"
    )


def _normalize_network_pks(my_following: Any) -> set[str]:
    if isinstance(my_following, dict):
        return {str(pk) for pk in my_following.keys()}

    if isinstance(my_following, (list, tuple, set)):
        normalized: set[str] = set()
        for item in my_following:
            if isinstance(item, dict):
                pk = item.get("pk")
            else:
                pk = getattr(item, "pk", None)
            if pk is not None:
                normalized.add(str(pk))
        return normalized

    return set()


def _build_results_table(results: list[tuple[str, str, str]]) -> Table:
    table = Table(
        show_header=False,
        box=box.SIMPLE,
        pad_edge=False,
        expand=False,
    )
    table.add_column("Status", no_wrap=True)
    table.add_column("Username", no_wrap=True)
    table.add_column("Name", overflow="fold")

    for status, username, name in results:
        if status == "+":
            prefix = "[success][+][/]"
        else:
            prefix = "[danger][?][/]"

        table.add_row(prefix, f"@{username}", name)

    return table


def scan(target: str, limit: int, output: str | None = None) -> None:
    started_at = time.time()
    log.info(f"Targeting [nx.pink]@{target}[/]...")

    try:
        with DotLoader("Loading target profile...", spinner="dots"):
            target_info = cl.user_info_by_username(target)
            target_id = target_info.pk
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "too many" in error_msg.lower():
            log.error(
                "[bold red]Rate limited by Instagram (429 Too Many Requests).[/]\nTry using a different account or waiting a few minutes."
            )
        else:
            log.error(f"Failed to fetch target info: {e}")
        return

    recommended_users: list[Any] = []
    try:
        with DotLoader("Loading recommendations...", spinner="dots"):
            chaining_data = (
                cl.user_chaining(target_id)
                if hasattr(cl, "user_chaining")
                else cl.chaining(target_id)
            )

            if isinstance(chaining_data, dict):
                recommended_users = chaining_data.get("users", [])
            else:
                recommended_users = chaining_data

            if recommended_users:
                chained_ids = ",".join(
                    str(u.get("pk") if isinstance(u, dict) else u.pk)
                    for u in recommended_users
                    if (u.get("pk") if isinstance(u, dict) else getattr(u, "pk", None))
                    is not None
                )
                try:
                    details_data = cl.fetch_suggestion_details(target_id, chained_ids)
                    recommended_users = details_data.get("users", recommended_users)
                except Exception:
                    pass

    except Exception as e:
        log.error(f"Failed to fetch recommendations: {e}")
        return

    if not recommended_users:
        log.warning("No recommendations found for this target.")
        return

    with DotLoader("Filtering relevant accounts...", spinner="dots"):
        filtered: list[Any] = []
        for u in recommended_users:
            u_pk, _, _ = _extract_user_fields(u)

            if u_pk is None:
                continue

            if isinstance(u, dict):
                mutual_count = u.get("mutual_followers_count", 0)
            else:
                mutual_count = getattr(u, "mutual_followers_count", 0)

            if mutual_count > 0:
                continue

            filtered.append(u)

    log.info(f"Found [accent]{len(filtered)}[/] relevant recommendations.")

    console.line()

    filtered = filtered[:limit]

    target_name_query = target

    results: list[tuple[str, str, str]] = []

    try:
        with DotLoader("Checking candidates...", spinner="dots") as status:
            for i, user in enumerate(filtered, 1):
                user_id, username, is_private = _extract_user_fields(user)
                full_name = _extract_user_name(user)

                if not username or user_id is None:
                    continue

                status.set_message(
                    f"Checking [nx.yellow]{i}/{len(filtered)}[/]: [accent]@{username}[/]"
                )

                if is_private:
                    results.append(("?", username, full_name))
                    continue

                try:
                    searched_followers = cl.search_followers(
                        str(user_id), target_name_query
                    )
                    searched_followers.extend(
                        cl.search_following(str(user_id), target_name_query)
                    )
                    found_target = False
                    for follower in searched_followers:
                        f_pk = (
                            getattr(follower, "pk", "")
                            if not isinstance(follower, dict)
                            else follower.get("pk", "")
                        )
                        if str(f_pk) == str(target_id):
                            found_target = True
                            break

                    if found_target:
                        results.append(("+", username, full_name))
                except PrivateError:
                    results.append(("?", username, full_name))
                except Exception as e:
                    if "Private" in str(e) or "Not authorized" in str(e):
                        results.append(("?", username, full_name))
                    else:
                        log.error(
                            f"Error fetching network for [accent]@{username}[/]: {e}"
                        )
    finally:
        pass

    console.print("[underline bold]Legend[/]")
    console.print("  [success][+][/] Found")
    console.print("  [danger][?][/] Private Account\n")

    if not results:
        console.print("[text.muted]No verifiable hits to display.[/]")
    else:
        console.print(_build_results_table(results))

    if output:
        try:
            with open(output, "w", encoding="utf-8") as f:
                for status, username, name in results:
                    f.write(f"[{status}] {username} {name}\n")
            log.info(f"Results saved to [accent]{output}[/].")
        except Exception as e:
            log.error(f"Failed to save results to {output}: {e}")

    elapsed_ms = int((time.time() - started_at) * 1000)
    console.print(f"\nScan completed in [accent]{elapsed_ms}ms[/].")


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    session_file = os.path.isfile(args.session)
    target = args.target.lstrip("@")

    print_banner()

    try:
        if args.login is not None:
            username = args.login.split(":")[0]
            try:
                password = args.login.split(":")[1]
            except IndexError:
                log.error("invalid -l/--login: use -l [accent]'username:pass'[/].")
                return 1
            login(credentials=(username, password))
        else:
            if not session_file:
                login()
            else:
                cl.load_settings(args.session)
    except KeyboardInterrupt:
        return 0
    except Exception as err:
        log.error(err)
        return 1

    scan(target, args.max, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
