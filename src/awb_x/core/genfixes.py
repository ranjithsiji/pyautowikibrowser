# AWB-X: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-X contributors
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

from awb_x.core.parsers.boldtitle import *
from awb_x.core.parsers.categorydefaultsort import *
from awb_x.core.parsers.citetemplates import *
from awb_x.core.parsers.fixdates import *
from awb_x.core.parsers.fixheadings import *
from awb_x.core.parsers.fixsyntax import *
from awb_x.core.parsers.hidetext import *
from awb_x.core.parsers.metadatasorter import *
from awb_x.core.parsers.multipleissues import *
from awb_x.core.parsers.parsers import *
from awb_x.core.parsers.references import *
from awb_x.core.parsers.sortmetadata import *
from awb_x.core.parsers.tagger import *
from awb_x.core.parsers.templates import *
from awb_x.core.parsers.unbalancedbrackets import *
from awb_x.core.parsers.wikilinks import *
from awb_x.core.summary import *
