#!/bin/sh
build_sphinx() {
  DOCDIR=$(dirname $SPHINX_MAKE)
  if [ -z "$NAME" ]; then
    conf_py=$(find $DOCDIR -name conf.py)
    NAME=$(awk '/project/ {gsub(/["'\'']/, ""); print $NF}' $conf_py)
    echo "NAME='$NAME'" >>$GITHUB_ENV
  fi

  if [ -f tox.ini ] && (tox -l | grep -q docs); then
    tox -e docs | tee doc_build.log
    BUILT_HTML="$(awk '/^The HTML pages are in/ { res = gensub(/^.*(\.tox\/.*)\.$/, "\\1"); print $NF; exit}' doc_build.log)"
  else
    if [ "$NEEDS_BUILD" = 'true' ]; then pip install -e .; fi
    test -f $DOCDIR/requirements.txt && pip install -r $DOCDIR/requirements.txt
    make -C $DOCDIR html | tee doc_build.log
    BUILT_HTML="$DOCDIR/$(awk '/^The HTML pages are in/ {sub(/\.$/, ""); print $NF; exit}' doc_build.log)"
  fi

  if [ -n "$BUILT_HTML" ]; then
    doc2dash ${NAME:+-n $NAME} ${ICON:+-i $DOCDIR/$ICON} "${BUILT_HTML}"
  else
    return 1
  fi
}

build_mkdocs() {
  SITE_DIR=$(mktemp -d tmp.XXXXXX)
  mkdocs build -t mkdocs -d $SITE_DIR
  rm -f $SITE_DIR/search_content.json

  # Recursively converts absolute links to relative links and protocol-relative links to https links
  python ../bin/abs2rel.py -v $SITE_DIR

  # Add Dash docs anchor tags to html source
  find $SITE_DIR -name "*.html" | xargs -n 1 python3 ../bin/add-dash-anchors.py

  # Package folder into Docset structure
  mkdir -p "$NAME".docset/Contents/Resources/Documents
  cp -a $SITE_DIR/* "$NAME".docset/Contents/Resources/Documents

  # Reads an MkDocs YAML file and generates a Docset SQLite3 index from the contents
  python3 ../bin/yaml2sqlite.py -v mkdocs.yml "$NAME".docset/Contents/Resources/docSet.dsidx

  # Add icons
  cp ../assets/docset/icon@2x.png "$NAME".docset/icon@2x.png
  cp ../assets/docset/icon.png "$NAME".docset/icon.png
  cat >"$NAME".docset/Contents/Info.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleIdentifier</key>
	<string>${NAME}</string>
	<key>CFBundleName</key>
	<string>${NAME}</string>
	<key>DashDocSetFamily</key>
	<string>dashtoc</string>
	<key>DocSetPlatformFamily</key>
	<string>${NAME}</string>
	<key>dashIndexFilePath</key>
	<string>index.html</string>
	<key>isJavaScriptEnabled</key>
	<true/>
	<key>isDashDocset</key>
	<true/>
</dict>
</plist>
EOF
}

setup() {
  pip install doc2dash sphinx-rtd-theme tox mkdocs lxml pyyaml
  git clone --depth 1 ${VERSION:+-b $VERSION} "${REPO}" repo
  cd repo
}

setup
SPHINX_MAKE=$(find doc* -name Makefile)
if [ -n "$SPHINX_MAKE" ]; then
  build_sphinx || exit 1
elif [ -f mkdocs.yml ]; then
  build_mkdocs || exit 1
else
  exit 1
fi
tar -czf ../${NAME}.tgz ${NAME}.docset
