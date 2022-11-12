#!/usr/bin/env python3

"""
Add Dash docs anchor tags to html source.
"""

import argparse
import re
import urllib.request, urllib.parse, urllib.error
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def dashrepl(match):
    (hopen, id, name, hclose) = match.group(1, 2, 3, 4)

    dashname = name
    dashname = re.sub("<.*?>", "", dashname)
    dashname = re.sub(r"[^a-zA-Z0-9\.\(\)\?',:; ]", "-", dashname)
    dashname = urllib.parse.quote(dashname)

    dash = f'<a name="//apple_ref/cpp/Section/{dashname}" class="dashAnchor"></a>'
    header = f'<h{hopen} id="{id}">{name}</h{hclose}>'
    return f"{dash}\n{header}"


def add_dash_anchors(filename: str|Path) -> None:
    with open(filename) as inf:
        html = inf.read()

    # Use regex to add dash docs anchors
    html = re.sub('<h([1-2]) id="(.*?)">(.*?)</h([1-2])>', dashrepl, html)

    with open(filename, "w") as f:
        f.write(html)

    logger.info("Added dash docs anchors to %s", filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add Dash docs anchor tags to html source."
    )
    parser.add_argument("filename", help="The html file to process.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.INFO)

    add_dash_anchors(args.filename)
