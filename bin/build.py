from __future__ import annotations
from pathlib import Path
import os
import subprocess
import re
from tempfile import mkdtemp
from . import abs2rel
from .add_dash_anchors import add_dash_anchors
from shutil import copytree, copy2
from .yaml2sqlite import yaml2sqlite
import click


def get_name(conf_py: Path) -> str:
    name = None
    with open(conf_py) as inf:
        for line in inf:
            if "project" in line:
                mo = re.match(r'.*=["\'](.*)["\']', line)
                if mo:
                    name = mo.expand(r"\1")
                    break
        if name is None:
            raise ValueError("Could not find project name in conf.py")
    with open(os.environ["GITHUB_ENV"]) as outf:
        outf.write(f"NAME={name}\n")
    return name


def run_tox() -> str:
    tox_e = subprocess.check_output(["tox", "-e", "docs"], text=True)
    for line in tox_e.splitlines():
        if line.startswith("The HTML pages are in"):
            built_html = line.split(" ")[-1].rsplit(".", 1)[0]
            return built_html
    raise ValueError("Could not find built HTML in tox output")


def build_sphinx(
    sphinx_make: Path,
    name: str | None = None,
    *,
    needs_build: bool = False,
    icon: str | None = None,
) -> None:
    DOCDIR = sphinx_make.parent
    built_html = None
    conf_py = next(DOCDIR.glob("**/conf.py"))
    if not name:
        name = get_name(conf_py)

    try:
        built_html = run_tox()
    except subprocess.CalledProcessError:
        if needs_build:
            subprocess.check_call(["pip", "install", "-e", "."])
            if os.path.exists(DOCDIR / "requirements.txt"):
                subprocess.check_call(
                    ["pip", "install", "-r", DOCDIR / "requirements.txt"]
                )
            make_log = subprocess.check_output(
                ["make", "-C", DOCDIR, "html"], text=True
            )
            for line in make_log.splitlines():
                if line.startswith("The HTML pages are in"):
                    built_html = line.split(" ")[-1].rsplit(".", 1)[0]

    if built_html:
        subprocess.check_call(
            ["doc2dash", "-n", name]
            + (["-i", DOCDIR / icon] if icon else [])
            + [built_html]
        )


def build_mkdocs(name: str):
    site_dir = Path(mkdtemp())
    out_dir = Path(f"{name}.docset")
    # call mkdoc to build the site
    subprocess.check_call(["mkdocs", "build", "-t", "mkdocs", "-d", site_dir])
    # remove search_content.json
    os.remove(site_dir / "search_content.json")

    # Recursively converts absolute links to relative links and protocol-relative links to https links
    abs2rel.main(str(site_dir))

    # Add Dash docs anchor tags to html source
    for html in site_dir.glob("**/*.html"):
        add_dash_anchors(html)

    # Package folder into Docset structure
    copytree(site_dir, out_dir / "Contents/Resources/Documents")

    # Reads an MkDocs YAML file and generates a Docset SQLite3 index from the contents
    yaml2sqlite("mkdocs.yml", out_dir / "Contents/Resources/docSet.dsidx")

    # Add icons

    copy2("../assets/docset/icon@2x.png", out_dir / "icon@2x.png")
    copy2("../assets/docset/icon.png", out_dir / "icon.png")
    with open(out_dir / "Contents/Info.plist") as outf:
        outf.write(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleIdentifier</key>
	<string>{name}</string>
	<key>CFBundleName</key>
	<string>{name}</string>
	<key>DashDocSetFamily</key>
	<string>dashtoc</string>
	<key>DocSetPlatformFamily</key>
	<string>{name}</string>
	<key>dashIndexFilePath</key>
	<string>index.html</string>
	<key>isJavaScriptEnabled</key>
	<true/>
	<key>isDashDocset</key>
	<true/>
</dict>
</plist>
"""
        )


@click.command()
@click.argument("repo")
@click.option("--name", default=None, envvar="NAME", help="Name of the docset")
@click.option(
    "--version",
    default=None,
    envvar="VERSION",
    help="Version of repo to use for the docset",
)
@click.option(
    "--icon", default=None, envvar="ICON", help="Path to icon inside doc directory"
)
@click.option(
    "--needs-build",
    is_flag=True,
    default=False,
    envvar="NEEDS_BUILD",
    help="Do we need to build the package first?",
)
def run(
    repo: str,
    name: str | None = None,
    version: str | None = None,
    icon: str | None = None,
    needs_build: bool = False,
):
    # run pip install
    subprocess.check_call(
        [
            "pip",
            "install",
            "-U",
            "doc2dash",
            "sphinx-rtd-theme",
            "tox",
            "mkdocs",
            "lxml",
            "pyyaml",
        ]
    )
    # clone git repo
    subprocess.check_call(
        ["git", "clone", "--depth", "1"]
        + (["-b", "version"] if version else [])
        + [repo, "repo"]
    )
    # change dir to repo
    os.chdir("repo")

    # find sphinx makefile
    try:
        sphinx_make = next(Path(".").glob("doc*/**/Makefile"))
    except StopIteration:
        if name:
            build_mkdocs(name)
    else:
        build_sphinx(sphinx_make, name, icon=icon, needs_build=needs_build)
    # tgz the docset
    subprocess.check_call(["tar", "-cvzf", f"../{name}.tgz", f"{name}.docset"])


if __name__ == "__main__":
    run()
