import sys
import os
from typing import TYPE_CHECKING


IS_SPHINX = os.path.basename(os.path.dirname(sys.argv[0])) == "sphinx"

if TYPE_CHECKING or IS_SPHINX:
    from urllib3.util import Retry  # noqa
