#!/usr/bin/env python3

"""
Recursively converts absolute links to relative links and protocol-relative
links to https links.
"""

import argparse
import os
import sys
import logging
import lxml.html

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class abs2rel:
    def __init__(self, path: str, root: str):
        self.path = path
        self.root = root

    def __call__(self, link):
        # convert protocol-relative links to https
        if link[:2] == "//":
            newlink = f"https:{link}"
        # convert absolute links to relative
        elif link[:1] == "/":
            # os.path.relpath('/foo', '/foo/bar/bav')
            #   => '../..'
            relpath = os.path.relpath(self.path, self.root)
            newlink = f"{relpath}{link}"
        else:
            newlink = link

        logger.debug("(abs2rel) old link: %s", link)
        logger.debug("(abs2rel) new link: %s", newlink)

        return newlink


def main(path: str, suffix: str = ".html") -> None:
    for root, dirs, files in os.walk(path):
        for fname in files:
            if fname.endswith(suffix):
                with open(os.path.join(root, fname)) as f:
                    page = f.read()
                logger.info("file: %s/%s", root, fname)
                html = lxml.html.fromstring(page)
                html.rewrite_links(abs2rel(path, root))

                # Write the updated links back to the file
                with open(os.path.join(root, fname), "wb") as f:
                    f.write(lxml.html.tostring(html, pretty_print=True))  # type: ignore [arg-type]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        help=(
            "The path containing files with links to convert "
            "from absolute to relative"
        ),
    )
    parser.add_argument(
        "--suffix",
        dest="suffix",
        default=".html",
        help="the suffixes of the files to convert",
    )
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
    parser.add_argument("-vv", dest="vverbose", action="store_true")
    args = parser.parse_args()

    if args.vverbose:
        logger.setLevel(logging.DEBUG)
    elif args.verbose:
        logger.setLevel(logging.INFO)

    if not os.path.isdir(args.path):
        logger.error("Error: Directory %s does not exist", args.path)
        sys.exit

    logger.info("Replacing absolute links with relative links")
