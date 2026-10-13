# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""All of AWB's Parsers in one namespace (the C# partial class Parsers, split here by file).

Ported code and tests use `genfixes.fix_links(...)` where AWB has `Parsers.FixLinks(...)`, and
`genfixes.Parsers()` for the instance methods.
"""

# ruff: noqa: F403
# pyright: reportWildcardImportFromLibrary=false

from pyawb.core.parsers.boldtitle import *
from pyawb.core.parsers.categorydefaultsort import *
from pyawb.core.parsers.citetemplates import *
from pyawb.core.parsers.fixdates import *
from pyawb.core.parsers.fixheadings import *
from pyawb.core.parsers.fixsyntax import *
from pyawb.core.parsers.hidetext import *
from pyawb.core.parsers.metadatasorter import *
from pyawb.core.parsers.multipleissues import *
from pyawb.core.parsers.parsers import *
from pyawb.core.parsers.references import *
from pyawb.core.parsers.sortmetadata import *
from pyawb.core.parsers.tagger import *
from pyawb.core.parsers.templates import *
from pyawb.core.parsers.unbalancedbrackets import *
from pyawb.core.parsers.wikilinks import *
from pyawb.core.summary import *
