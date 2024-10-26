import json
from unittest import mock

import pytest
from click.testing import CliRunner

import pyairtable.cli
import pyairtable.orm.generate
from pyairtable.testing import fake_id


@pytest.fixture
def user_id():
    return "usrL2PNC5o3H4lBEi"


@pytest.fixture(autouse=True)
def mock_metadata(
    api,
    user_id,
    mock_base_metadata,
    mock_workspace_metadata,
    enterprise,
    requests_mock,
    sample_json,
):
    user_info = sample_json("UserInfo")
    user_group = sample_json("UserGroup")
    enterprise_info = sample_json("EnterpriseInfo")
    requests_mock.get(api.urls.whoami, json={"id": user_id})
    requests_mock.get(enterprise.urls.meta, json=enterprise_info)
    requests_mock.get(enterprise.urls.users, json={"users": [user_info]})
    requests_mock.get(enterprise.urls.user(user_id), json=user_info)
    for group_id in enterprise_info["groupIds"]:
        requests_mock.get(enterprise.urls.group(group_id), json=user_group)


@pytest.fixture
def run(mock_metadata, monkeypatch):
    default_env = {"AIRTABLE_API_KEY": "test"}

    def _runner(*args: str, env: dict = default_env, fails: bool = False):
        # make sure we're starting from a blank environment
        monkeypatch.delenv("AIRTABLE_API_KEY", raising=False)
        monkeypatch.delenv("AIRTABLE_API_KEY_FILE", raising=False)
        # run the command
        runner = CliRunner(env=env)
        result = runner.invoke(pyairtable.cli.cli, args)
        # if a test fails, show the command's output
        print(f"{result.output=}")
        if fails and result.exit_code == 0:
            raise RuntimeError("expected failure, but command succeeded")
        if result.exit_code != 0 and not fails:
            print(f"{result.exception=}")
            if hasattr(result.exception, "request"):
                print(f"{result.exception.request.url=}")
            raise RuntimeError(f"command failed: {args}")
        return result

    def _runner_with_json(*args, **kwargs):
        result = _runner(*args, **kwargs)
        assert result.stdout, "command did not produce any output"
        return json.loads(result.stdout)

    _runner.json = _runner_with_json

    return _runner


def test_help(run):
    """
    Test that the --help message lists the correct top-level commands.
    """
    result = run("--help")
    lines = result.output.split("Commands:", 1)[1].splitlines()
    defined_commands = set(pyairtable.cli.CLI_COMMANDS)
    listed_commands = set(line.strip().split("  ")[0] for line in lines)
    assert not defined_commands - listed_commands


def test_error_without_key(run):
    result = run("whoami", env={}, fails=True)
    assert "--key, --key-file, or --key-env required" in result.output


def test_error_invalid_command(run):
    run("asdf", fails=True)


def test_invalid_key_args(run, tmp_path):
    keyfile = tmp_path / "keyfile.txt"
    keyfile.write_text("fakeKey")
    for args in [
        ("--key", "key", "--key-file", keyfile),
        ("--key", "key", "--key-env", "key"),
        ("--key-env", "key", "--key-file", keyfile),
    ]:
        result = run(*args, "whoami", env={}, fails=True)
        print(args)
        assert "only one of --key, --key-file, --key-env allowed" in result.output


@pytest.mark.parametrize("cmd", ["whoami", "who", "w"])  # test alias
def test_whoami(run, cmd, user_id):
    result = run.json(cmd)
    assert result == {"id": user_id}


@pytest.mark.parametrize("option", ["-k", "--key"])
def test_whoami__key(run, option, user_id):
    result = run.json(option, "key", "whoami", env={})
    assert result == {"id": user_id}


@pytest.mark.parametrize("option", ["-ke", "--key-env"])
def test_whoami__keyenv(run, option, user_id):
    env = {"THE_KEY": "fakeKey"}
    result = run.json(option, "THE_KEY", "whoami", env=env)
    assert result == {"id": user_id}


@pytest.mark.parametrize("option", ["-kf", "--key-file"])
def test_whoami__keyfile(run, option, user_id, tmp_path):
    keyfile = tmp_path / "keyfile.txt"
    keyfile.write_text("fakeKey")
    result = run.json(option, keyfile, "whoami", env={})
    assert result == {"id": user_id}


def test_bases(run, base):
    result = run.json("bases")
    assert len(result) == 2
    assert result[0]["id"] == base.id


def test_base(run):
    result = run("base", fails=True)
    assert "Missing argument 'BASE_ID'" in result.output


@pytest.mark.parametrize("cmd", ["orm", "o"])  # test alias
def test_base_orm(base, run, cmd):
    result = run("base", base.id, cmd)
    expected = str(pyairtable.orm.generate.ModelFileBuilder(base))
    assert result.output.rstrip().endswith(expected)


@pytest.mark.parametrize("extra_args", [[], ["schema"]])
def test_base_schema(run, base, extra_args):
    result = run.json("base", base.id, *extra_args)
    assert list(result) == ["tables"]
    assert result["tables"][0]["name"] == "Apartments"


@pytest.mark.parametrize("cmd", ["records", "r"])  # test alias
@pytest.mark.parametrize(
    "extra_args,expected_kwargs",
    [
        ([], {}),
        (["-f", "$formula"], {"formula": "$formula"}),
        (["--formula", "$formula"], {"formula": "$formula"}),
        (["-v", "$view"], {"view": "$view"}),
        (["--view", "$view"], {"view": "$view"}),
        (["-n", 10], {"max_records": 10}),
        (["--limit", 10], {"max_records": 10}),
        (["-F", "$fld1", "--field", "$fld2"], {"fields": ["$fld1", "$fld2"]}),
        (["-S", "fld1", "--sort", "-fld2"], {"sort": ["fld1", "-fld2"]}),
    ],
)
@mock.patch("pyairtable.Table.all")
def test_base_table_records(
    mock_table_all, run, cmd, base, extra_args, expected_kwargs
):
    defaults = {
        "formula": None,
        "view": None,
        "max_records": None,
        "fields": [],
        "sort": [],
    }
    expected = {**defaults, **expected_kwargs}
    fake_ids = [fake_id() for _ in range(3)]
    mock_table_all.return_value = [{"id": id} for id in fake_ids]
    result = run.json("base", base.id, "table", "Apartments", cmd, *extra_args)
    mock_table_all.assert_called_once_with(**expected)
    assert len(result) == 3
    assert set(record["id"] for record in result) == set(fake_ids)


@pytest.mark.parametrize("extra_args", [[], ["schema"]])
def test_base_table_schema(run, base, extra_args):
    result = run.json("base", base.id, "table", "Apartments", *extra_args)
    assert result["fields"][0]["id"] == "fld1VnoyuotSTyxW1"


@pytest.mark.parametrize("cmd", ["c", "collaborators"])
def test_base_collaborators(run, base, cmd):
    result = run.json("base", base.id, cmd)
    assert result["id"] == base.id
    assert result["collaborators"]["baseCollaborators"][0]["email"] == "foo@bam.com"


@pytest.mark.parametrize("cmd", ["sh", "shares"])
def test_base_shares(run, base, cmd):
    result = run.json("base", base.id, cmd)
    assert result[0]["shareId"] == "shr9SpczJvQpfAzSp"


@pytest.mark.parametrize("cmd", ["e", "enterprise"])
@pytest.mark.parametrize("extra_args", [[], ["info"]])
def test_enterprise_info(run, enterprise, cmd, extra_args):
    result = run.json(cmd, enterprise.id, *extra_args)
    assert result["id"] == enterprise.id


def test_enterprise_user(run, enterprise, user_id):
    result = run.json("enterprise", enterprise.id, "user", user_id)
    assert result["id"] == user_id
    assert result["email"] == "foo@bar.com"


def test_enterprise_users(run, enterprise, user_id):
    result = run.json("enterprise", enterprise.id, "users", user_id)
    assert list(result) == [user_id]
    assert result[user_id]["id"] == user_id
    assert result[user_id]["email"] == "foo@bar.com"


def test_enterprise_users__all(run, enterprise, user_id):
    result = run.json("enterprise", enterprise.id, "users", "--all")
    assert list(result) == [user_id]
    assert result[user_id]["id"] == user_id
    assert result[user_id]["email"] == "foo@bar.com"


def test_enterprise_users__invalid(run, enterprise, user_id):
    run("enterprise", enterprise.id, "users", fails=True)
    run("enterprise", enterprise.id, "users", "--all", user_id, fails=True)


def test_enterprise_group(run, enterprise):
    result = run.json("enterprise", enterprise.id, "group", "ugp1mKGb3KXUyQfOZ")
    assert result["id"] == "ugp1mKGb3KXUyQfOZ"
    assert result["name"] == "Group name"


@pytest.mark.parametrize("option", ["ugp1mKGb3KXUyQfOZ", "-a", "--all"])
def test_enterprise_groups(run, enterprise, option):
    result = run.json("enterprise", enterprise.id, "groups", option)
    assert list(result) == ["ugp1mKGb3KXUyQfOZ"]
    assert result["ugp1mKGb3KXUyQfOZ"]["id"] == "ugp1mKGb3KXUyQfOZ"
    assert result["ugp1mKGb3KXUyQfOZ"]["name"] == "Group name"


def test_enterprise_groups__invalid(run, enterprise):
    run("enterprise", enterprise.id, "groups", fails=True)
    run("enterprise", enterprise.id, "groups", "--all", "ugp1mKGb3KXUyQfOZ", fails=True)
