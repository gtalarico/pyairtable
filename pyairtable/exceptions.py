class PyAirtableError(Exception):
    """
    Base class for all exceptions raised by PyAirtable.
    """


class CircularFormulaError(PyAirtableError, RecursionError):
    """
    A circular dependency was encountered when flattening nested conditions.
    """


class InvalidParameterError(PyAirtableError, ValueError):
    """
    Raised when invalid parameters are passed to ``all()``, ``first()``, etc.
    """


class MissingValueError(PyAirtableError, ValueError):
    """
    A required field received an empty value, either from Airtable or other code.
    """


class MultipleValuesError(PyAirtableError, ValueError):
    """
    SingleLinkField received more than one value from either Airtable or calling code.
    """


class ReadonlyFieldError(PyAirtableError, ValueError):
    """
    Attempted to set a value on a readonly field.
    """


class UnsavedRecordError(PyAirtableError, ValueError):
    """
    Attempted to perform an unsupported operation on an unsaved record.
    """
