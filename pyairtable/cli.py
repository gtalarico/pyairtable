"""
pyAirtable exposes a command-line interface that allows you to interact with the API.
"""

import functools
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Optional, Sequence, Tuple, Union

from click import Context, HelpFormatter
from typing_extensions import ParamSpec, TypeVar

from pyairtable.api.api import Api
from pyairtable.api.base import Base
from pyairtable.api.enterprise import Enterprise
from pyairtable.api.table import Table
from pyairtable.models._base import AirtableModel
from pyairtable.orm.generate import ModelFileBuilder
from pyairtable.utils import chunked, is_table_id

try:
    import click
except ImportError:  # pragma: no cover
    print(
        "You are missing the 'click' library, which means you did not install\n"
        "the optional dependencies required for the pyairtable command line.\n"
        "Try again after running:\n\n"
        "   % pip install 'pyairtable[cli]'",
        "\n",
        file=sys.stderr,
    )
    raise


T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")


@dataclass
class CliContext:
    access_token: str = ""
    base_id: str = ""
    table_id_or_name: str = ""
    enterprise_id: str = ""
    click_context: Optional["click.Context"] = None

    @functools.cached_property
    def api(self) -> Api:
        return Api(self.access_token)

    @functools.cached_property
    def base(self) -> Base:
        return self.api.base(self.base_id)

    @functools.cached_property
    def table(self) -> Table:
        return self.base.table(self.table_id_or_name)

    @functools.cached_property
    def enterprise(self) -> Enterprise:
        return self.api.enterprise(self.enterprise_id)

    @property
    def click(self) -> click.Context:
        assert self.click_context is not None
        return self.click_context

    def default_subcommand(self, cmd: F) -> None:
        if not self.click.invoked_subcommand:
            self.click.invoke(cmd)


def needs_context(func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    @click.pass_context
    def _wrapped(click_ctx: click.Context, /, *args: P.args, **kwargs: P.kwargs) -> T:
        obj = click_ctx.ensure_object(CliContext)
        obj.click_context = click_ctx
        return click_ctx.invoke(func, obj, *args, **kwargs)

    return _wrapped


class ShortcutGroup(click.Group):
    """
    A command group that will accept partial command names and complete them.
    """

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        if exact := super().get_command(ctx, cmd_name):
            return exact
        # If exactly one subcommand starts with the given name, use that.
        existing = [cmd for cmd in self.list_commands(ctx) if cmd.startswith(cmd_name)]
        if len(existing) == 1:
            return super().get_command(ctx, existing[0])
        return None

    def format_commands(self, ctx: Context, formatter: HelpFormatter) -> None:
        from gettext import gettext as _

        rows = [
            (name, (command.short_help or command.help or "").strip())
            for name, command in CLI_COMMANDS.items()
        ]
        col_max = max(len(row[0]) for row in rows)

        with formatter.section(_("Commands")):
            formatter.write_dl(rows, col_max=col_max)


# fmt: off
@click.group(cls=ShortcutGroup)
@click.option("-k", "--key", help="Your API key.")
@click.option("-kf", "--key-file", type=click.Path(exists=True), help="File containing your API key.")
@click.option("-ke", "--key-env", metavar="VAR", help="Env var containing your API key.")
@click.option("-v", "--verbose", is_flag=True, help="Print verbose output.")
@needs_context
# fmt: on
def cli(
    ctx: CliContext,
    key: str = "",
    key_file: str = "",
    key_env: str = "",
    verbose: bool = False,
) -> None:
    if not any([key, key_file, key_env]):
        try:
            key_file = os.environ["AIRTABLE_API_KEY_FILE"]
        except KeyError:
            try:
                key = os.environ["AIRTABLE_API_KEY"]
            except KeyError:
                raise click.UsageError("--key, --key-file, or --key-env required")

    if len([arg for arg in (key, key_file, key_env) if arg]) > 1:
        raise click.UsageError("only one of --key, --key-file, --key-env allowed")

    if key_file:
        with open(key_file) as inputf:
            key = inputf.read().strip()

    if key_env:
        key = os.environ[key_env]

    ctx.access_token = key


@cli.command()
@needs_context
def whoami(ctx: CliContext) -> None:
    """
    Print the current user's information.
    """
    _dump(ctx.api.whoami())


@cli.command()
@needs_context
def bases(ctx: CliContext) -> None:
    """
    List all available bases.
    """
    _dump(ctx.api._base_info().bases)


@cli.group(invoke_without_command=True, cls=ShortcutGroup)
@click.argument("base_id")
@needs_context
def base(ctx: CliContext, base_id: str) -> None:
    """
    Print information about a base.
    """
    ctx.base_id = base_id
    ctx.default_subcommand(base_schema)


@base.command("schema")
@needs_context
def base_schema(ctx: CliContext) -> None:
    """
    Print the base schema.
    """
    _dump(ctx.base.schema())


@base.group("table", invoke_without_command=True, cls=ShortcutGroup)
@needs_context
@click.argument("id_or_name")
def base_table(ctx: CliContext, id_or_name: str) -> None:
    """
    Print information about a table.
    """
    ctx.table_id_or_name = id_or_name
    ctx.default_subcommand(base_table_schema)


@base_table.command("records")
@needs_context
# fmt: off
@click.option("-f", "--formula", help="Filter records with a formula.")
@click.option("-v", "--view", help="Filter records by a view.")
@click.option("-n", "--limit", "max_records", type=int, help="Limit the number of records returned.")
@click.option("-S", "--sort", help="Sort records by field(s).", multiple=True)
@click.option("-F", "--field", "fields", help="Limit output to certain field(s).", multiple=True)
# fmt: on
def base_table_records(
    ctx: CliContext,
    formula: Optional[str],
    view: Optional[str],
    max_records: Optional[int],
    fields: Sequence[str],
    sort: Sequence[str],
) -> None:
    """
    Retrieve records from the table.
    """
    fields = list(fields)
    sort = list(sort)
    _dump(
        ctx.table.all(
            formula=formula,
            view=view,
            max_records=max_records,
            fields=fields,
            sort=sort,
        )
    )


@base_table.command("schema")
@needs_context
def base_table_schema(ctx: CliContext) -> None:
    """
    Print the table's schema as JSON.
    """
    _dump(ctx.table.schema())


@base.command("collaborators")
@needs_context
def base_collaborators(ctx: CliContext) -> None:
    """
    Print base collaborators.
    """
    _dump(ctx.base.collaborators())


@base.command("shares")
@needs_context
def base_shares(ctx: CliContext) -> None:
    """
    Print base shares.
    """
    _dump(ctx.base.shares())


@base.command("orm")
@needs_context
@click.option(
    "-t",
    "--table",
    help="Only generate specific table(s).",
    metavar="NAME_OR_ID",
    multiple=True,
)
def base_orm(ctx: CliContext, table: Sequence[str]) -> None:
    """
    Generate a Python ORM module.
    """
    table_ids = [t for t in table if is_table_id(t)]
    table_names = [t for t in table if not is_table_id(t)]
    generator = ModelFileBuilder(ctx.base, table_ids=table_ids, table_names=table_names)
    now = datetime.now(timezone.utc).isoformat()
    print("# This file was generated by pyAirtable at", now)
    print("# Any modifications to this file will be lost if it is rebuilt.")
    print()
    print(str(generator))


@cli.group(invoke_without_command=True, cls=ShortcutGroup)
@click.argument("enterprise_id")
@needs_context
def enterprise(ctx: CliContext, enterprise_id: str) -> None:
    """
    Print information about a user.
    """
    ctx.enterprise_id = enterprise_id
    ctx.default_subcommand(enterprise_info)


@enterprise.command("info")
@needs_context
def enterprise_info(ctx: CliContext) -> None:
    """
    Print information about an enterprise.
    """
    _dump(ctx.enterprise.info())


@enterprise.command("user")
@needs_context
@click.argument("id_or_email")
def enterprise_user(ctx: CliContext, id_or_email: str) -> None:
    """
    Print one user's information.
    """
    _dump(ctx.enterprise.user(id_or_email))


@enterprise.command("users")
@needs_context
@click.argument("ids_or_emails", metavar="ID_OR_EMAIL...", nargs=-1)
@click.option("-c", "--collaborations", is_flag=True, help="Include collaborations.")
@click.option("-a", "--all", "all_users", is_flag=True, help="Retrieve all users.")
def enterprise_users(
    ctx: CliContext,
    ids_or_emails: Sequence[str],
    collaborations: bool = False,
    all_users: bool = False,
) -> None:
    """
    Print many users, keyed by user ID.
    """
    if all_users and ids_or_emails:
        raise click.UsageError("Cannot combine --all with specific user IDs/emails.")
    if all_users:
        ids_or_emails = list(ctx.enterprise.info().user_ids)
    if not ids_or_emails:
        raise click.UsageError("No user IDs or emails provided.")
    _dump(
        {
            user.id: user._raw
            for chunk in chunked(ids_or_emails, 100)
            for user in ctx.enterprise.users(chunk, collaborations=collaborations)
        }
    )


@enterprise.command("group")
@needs_context
@click.argument("group_id")
def enterprise_group(ctx: CliContext, group_id: str) -> None:
    """
    Print a user group's information.
    """
    _dump(ctx.enterprise.group(group_id))


@enterprise.command("groups")
@needs_context
@click.argument("group_ids", metavar="GROUP_ID...", nargs=-1)
@click.option("-a", "--all", "all_groups", is_flag=True, help="Retrieve all groups.")
@click.option("-c", "--collaborations", is_flag=True, help="Include collaborations.")
def enterprise_groups(
    ctx: CliContext,
    group_ids: Sequence[str],
    all_groups: bool = False,
    collaborations: bool = False,
) -> None:
    """
    Print many groups, keyed by group ID.
    """
    if all_groups and group_ids:
        raise click.UsageError("Cannot combine --all with specific group IDs.")
    if all_groups:
        group_ids = list(ctx.enterprise.info().group_ids)
    if not group_ids:
        raise click.UsageError("No group IDs provided.")
    _dump(
        {
            group.id: group._raw
            for group_id in group_ids
            if (group := ctx.enterprise.group(group_id, collaborations=collaborations))
        }
    )


class JSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, AirtableModel):
            return o._raw
        return super().default(o)  # pragma: no cover


def _dump(obj: Any) -> None:
    print(json.dumps(obj, cls=JSONEncoder))


def _gather_commands(
    command: Union[click.Command, click.Group] = cli,
    prefix: str = "",
) -> Iterator[Tuple[str, Union[click.Command, click.Group]]]:
    """
    Enumerate through all commands and groups, yielding a 2-tuple of
    a human-readable command line and the associated function.
    """
    # placeholders for arguments so we make a valid testable command
    if command.name != cli.name:
        prefix = f"{prefix} {command.name}".strip()

    for param in command.params:
        if not isinstance(param, click.Argument):
            continue
        if param.required or (param.metavar and param.metavar.endswith("...")):
            metavar = (param.metavar or param.name or "ARG").upper()
            metavar = re.sub(r"\b[A-Z]+_ID", "ID", metavar)
            prefix = f"{prefix} {metavar}".strip()

    if not isinstance(command, click.Group):
        yield (prefix, command)
        return

    for subcommand in command.commands.values():
        yield from _gather_commands(subcommand, prefix=prefix)


#: Mapping of command names to their functions.
CLI_COMMANDS = dict(_gather_commands(cli))


if __name__ == "__main__":
    cli()  # pragma: no cover
