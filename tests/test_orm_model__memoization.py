from unittest.mock import Mock

import pytest

from pyairtable.orm import Model
from pyairtable.orm import fields as f
from pyairtable.testing import fake_meta, fake_record


class Author(Model):
    Meta = fake_meta(memoize=True)
    name = f.TextField("Name")
    books = f.LinkField["Book"]("Books", "Book")


class Book(Model):
    Meta = fake_meta()
    name = f.TextField("Title")
    author = f.SingleLinkField("Author", Author)


@pytest.fixture(autouse=True)
def clear_memoization_and_forbid_api_calls(requests_mock):
    Author._memoized.clear()
    Book._memoized.clear()


@pytest.fixture
def record_mocks(requests_mock):
    mocks = Mock()
    mocks.authors = {
        record["id"]: record
        for record in [
            fake_record(Name="Abigail Adams"),
            fake_record(Name="Babette Brown"),
            fake_record(Name="Cristina Cubas"),
        ]
    }
    mocks.books = {
        record["id"]: record
        for author_id, n in zip(mocks.authors, range(3))
        if (record := fake_record(Title=f"Book {n}", Author=[author_id]))
    }
    for book_id, book_record in mocks.books.items():
        author_record = mocks.authors[book_record["fields"]["Author"][0]]
        author_record["fields"]["Books"] = [book_id]

    # for Model.all
    mocks.get_authors = requests_mock.get(
        Author.meta.table.urls.records,
        json={"records": list(mocks.authors.values())},
    )
    mocks.get_books = requests_mock.get(
        Book.meta.table.urls.records,
        json={"records": list(mocks.books.values())},
    )

    # for Model.from_id
    mocks.get_author = {
        record_id: requests_mock.get(
            Author.meta.table.urls.record(record_id), json=record_data
        )
        for record_id, record_data in mocks.authors.items()
    }
    mocks.get_book = {
        record_id: requests_mock.get(
            Book.meta.table.urls.record(record_id), json=record_data
        )
        for record_id, record_data in mocks.books.items()
    }
    mocks.get = {**mocks.get_author, **mocks.get_book}

    return mocks


parametrized_memoization_test = pytest.mark.parametrize(
    "cls,kwargs,expect_memoized",
    [
        # Meta.memoize is True, memoize= is not provided
        (Author, {}, True),
        # Meta.memoize is True, memoize=False
        (Author, {"memoize": False}, False),
        # Meta.memoize is False, memoize= is not provided
        (Book, {}, False),
        # Meta.memoize is False, memoize=True
        (Book, {"memoize": True}, True),
    ],
)


@parametrized_memoization_test
def test_memoize__from_record(cls, kwargs, expect_memoized):
    """
    Test whether Model.from_record saves objects to Model._memoized
    """
    obj = cls.from_record(fake_record(), **kwargs)
    assert_memoized(obj, expect_memoized)


@parametrized_memoization_test
def test_memoize__from_id(record_mocks, cls, kwargs, expect_memoized):
    """
    Test whether Model.from_id saves objects to Model._memoized
    """
    record_id = list(getattr(record_mocks, cls.__name__.lower() + "s"))[0]
    obj = cls.from_id(record_id, **kwargs)
    assert record_mocks.get[record_id].call_count == 1
    assert_memoized(obj, expect_memoized)


@parametrized_memoization_test
def test_memoize__all(record_mocks, cls, kwargs, expect_memoized):
    """
    Test whether Model.all saves objects to Model._memoized
    """
    for obj in cls.all(**kwargs):
        assert_memoized(obj, expect_memoized)


@parametrized_memoization_test
def test_memoize__first(record_mocks, cls, kwargs, expect_memoized):
    """
    Test whether Model.all saves objects to Model._memoized
    """
    assert_memoized(cls.first(**kwargs), expect_memoized)


def assert_memoized(obj: Model, expect_memoized: bool = True):
    if expect_memoized:
        assert obj.__class__._memoized[obj.id] is obj
    else:
        assert obj.id not in obj.__class__._memoized


def test_from_id():
    """
    Test that Model.from_id pulls from Model._memoized, regardless
    of whether Model.Meta.memoize is True or False.
    """
    book = Book.from_record(fake_record())
    Book._memoized[book.id] = book
    assert Book.from_id(book.id) is book


def test_from_ids(record_mocks):
    """
    Test that Model.from_ids pulls from Model._memoized, regardless
    of whether Model.Meta.memoize is True or False.
    """
    book = Book.from_record(fake_record())
    Book._memoized = {book.id: book}
    books = Book.from_ids([book.id, *list(record_mocks.books)])
    # We got all four, but only requested the non-memoized three from the API
    assert len(books) == 4
    assert record_mocks.get_books.call_count == 1
    assert record_mocks.get_books.last_request.qs["filterByFormula"] == [
        "OR(%s)" % ", ".join(f"RECORD_ID()='{id}'" for id in sorted(record_mocks.books))
    ]


def test_memoize__link_field(record_mocks):
    """
    Test that Model.link_field writes to Model._memoized if Model.Meta.memoize is True
    """
    book_id = list(record_mocks.books)[0]
    book = Book.from_id(book_id)
    assert record_mocks.get[book_id].call_count == 1

    # no memoization yet
    assert not Book._memoized
    assert not Author._memoized

    book.author  # this makes the call
    assert book.author.id == record_mocks.books[book_id]["fields"]["Author"][0]
    assert Author._memoized[book.author.id] is book.author

    # test that we only ever made one network call per object
    assert record_mocks.get[book.id].call_count == 1
    assert record_mocks.get[book.author.id].call_count == 0
    assert record_mocks.get_authors.call_count == 1
    assert record_mocks.get_authors.last_request.qs["filterByFormula"] == [
        f"OR(RECORD_ID()='{book.author.id}')"
    ]


def test_memoize__link_field__populate(record_mocks):
    """
    Test that Model.link_field.populate writes to Model._memoized if memoize=True
    """
    author_id = list(record_mocks.authors)[0]
    author = Author.from_id(author_id)
    Author.books.populate(author, memoize=True)
    assert len(author.books) == 1
    for book in author.books:
        assert Book._memoized[book.id] is book
        assert record_mocks.get[book.id].call_count == 0
    # test that we only ever made one network call
    assert record_mocks.get_books.call_count == 1
    assert record_mocks.get_books.last_request.qs["filterByFormula"] == [
        "OR(%s)" % ", ".join(f"RECORD_ID()='{book.id}'" for book in author.books)
    ]
