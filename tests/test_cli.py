import json
from unittest import mock

import pytest
from click.testing import CliRunner

import pyairtable.cli
import pyairtable.orm.generate
from pyairtable.testing import fake_id


@pytest.fixture
def user_id(api, requests_mock):
    user_id = fake_id("usr")
    requests_mock.get(api.build_url("meta/whoami"), json={"id": user_id})
    return user_id


@pytest.fixture(autouse=True)
def mock_metadata(user_id, mock_base_metadata, mock_workspace_metadata):
    pass


@pytest.fixture
def run(mock_base_metadata):
    default_env = {"AIRTABLE_API_KEY": "test"}

    def _runner(*args: str, env: dict = default_env, fails: bool = False):
        runner = CliRunner(env=env)
        result = runner.invoke(pyairtable.cli.cli, args)
        print(result.output)  # if a test fails, show the command's output
        if fails:
            assert result.exit_code != 0
        else:
            assert result.exit_code == 0
        return result

    def _runner_with_json(*args, **kwargs):
        result = _runner(*args, **kwargs)
        return json.loads(result.stdout)

    _runner.json = _runner_with_json

    return _runner


def test_help(run):
    result = run("--help")
    commands = [
        words[0]
        for line in result.output.split("Commands:", 1)[1].splitlines()
        if (words := line.strip().split())
    ]
    assert commands == ["base", "bases", "whoami"]


def test_error_without_key(run):
    result = run("whoami", env={}, fails=True)
    assert "--key, --key-file, or --key-env required" in result.output


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


def test_whoami(run, user_id):
    result = run.json("whoami")
    assert result == {"id": user_id}


def test_whoami__key(run, user_id):
    result = run.json("-k", "key", "whoami", env={})
    assert result == {"id": user_id}


def test_whoami__keyenv(run, user_id):
    env = {"THE_KEY": "fakeKey"}
    result = run.json("-ke", "THE_KEY", "whoami", env=env)
    assert result == {"id": user_id}


def test_whoami__keyfile(run, user_id, tmp_path):
    keyfile = tmp_path / "keyfile.txt"
    keyfile.write_text("fakeKey")
    result = run.json("-kf", keyfile, "whoami", env={})
    assert result == {"id": user_id}


def test_bases(run, base):
    result = run.json("bases")
    assert len(result) == 2
    assert result[0]["id"] == base.id


def test_base(run):
    result = run("base", fails=True)
    assert "Missing argument 'BASE_ID'" in result.output


def test_base_orm(base, run):
    result = run("base", base.id, "orm")
    expected = str(pyairtable.orm.generate.ModelFileBuilder(base))
    assert result.output.rstrip().endswith(expected)


@pytest.mark.parametrize("extra_args", [[], ["schema"]])
def test_base_schema(run, base, extra_args):
    result = run.json("base", base.id, *extra_args)
    assert list(result) == ["tables"]
    assert result["tables"][0]["name"] == "Apartments"


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
def test_base_table_records(mock_table_all, run, base, extra_args, expected_kwargs):
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
    result = run.json("base", base.id, "table", "Apartments", "records", *extra_args)
    mock_table_all.assert_called_once_with(**expected)
    assert len(result) == 3
    assert set(record["id"] for record in result) == set(fake_ids)


@pytest.mark.parametrize("extra_args", [[], ["schema"]])
def test_base_table_schema(run, base, extra_args):
    result = run.json("base", base.id, "table", "Apartments", *extra_args)
    assert result["fields"][0]["id"] == "fld1VnoyuotSTyxW1"
