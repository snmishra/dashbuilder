#!/usr/bin/env python3

"""
Reads an MkDocs YAML file and generates a Docset SQLite3 index from the
contents.
"""

import argparse
import os
import re
import sqlite3
import sys
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def yaml2sqlite(yamlfile: str | Path, sqlitefile: str | Path) -> None:
    # Set up db
    db = sqlite3.connect(sqlitefile)
    cur = db.cursor()

    cur.execute(
        """
        DROP TABLE IF EXISTS searchIndex;
    """
    )

    cur.execute(
        """
        CREATE TABLE
            searchIndex(id INTEGER PRIMARY KEY,
                        name TEXT,
                        type TEXT,
                        path TEXT);
    """
    )

    cur.execute(
        """
        CREATE UNIQUE INDEX
            anchor
        ON
            searchIndex (name, type, path);
    """
    )

    db.commit()

    # Read YAML and iterate over entries
    with open(yamlfile) as f:
        rawyaml = f.read()

    if rawyaml:
        prevtitle = ""
        config = yaml.load(rawyaml, yaml.Loader)
        pages = config.get("pages") or config.get("nav")
        for page in pages:
            title = list(page.keys())[0]
            mdpath = list(page.values())[0]
            if "**HIDDEN**" in title:
                continue
            if "index.md" in mdpath:
                htmlpath = mdpath.replace("index.md", "index.html")
            else:
                htmlpath = mdpath.replace(".md", "/index.html")

            # Replace bullets with breadcrumbs
            if "&blacksquare;" in title:
                title = re.sub(r".*&blacksquare;&nbsp;\s*", prevtitle + " - ", title)
            else:
                prevtitle = title

            cur.execute(
                """
                INSERT OR IGNORE INTO
                    searchIndex(name, type, path)
                VALUES
                    (?, ?, ?);
            """,
                (title, "Guide", htmlpath),
            )

            db.commit()

            logger.info(
                "Added the following entry to %s:\n    name: %s\n    type: %s\n    path: %s",
                sqlitefile,
                title,
                "Guide",
                htmlpath,
            )

    db.close()


if __name__ == "__maine__":
    parser = argparse.ArgumentParser()
    parser.add_argument("yaml", help=("The MkDocs YAML file to convert to a SQLite DB"))
    parser.add_argument("sqlite", help=("The SQLite DB file to create"))
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    if not os.path.isfile(args.yaml):
        print("Error: Directory %s does not exist" % args.path)
        sys.exit(1)
