#!/bin/sh
pip install doc2dash sphinx-rtd-theme tox
git clone --depth 1 "${REPO}" repo
cd repo
DOCDIR=$(dirname $(find doc* -name Makefile))
if [ -z "$NAME" ] ; then
  conf_py=$(find $DOCDIR -name conf.py)
  NAME=$(awk '/project/ {gsub(/["'\'']/, ""); print $NF}' $conf_py)
fi

if [ -f tox.ini ] && (tox -l | grep -q docs); then
  tox -e docs
else
  if [ "$NEEDS_BUILD" = 'true' ] ; then pip install -e .; fi
  test -f $DOCDIR/requirements.txt && pip install -r $DOCDIR/requirements.txt
  make -C $DOCDIR html | tee doc_build.log
fi

BUILT_HTML=$(awk '/The HTML pages are in/ {sub(/\.$/, ""); print $NF}' doc_build.log)
if [ -n "$BUILT_HTML" ]; then
  doc2dash ${NAME:+-n $NAME} ${ICON:+-i $DOCDIR/$ICON} "$DOCDIR/${BUILT_HTML:-_build/html}"
  tar -czf ${NAME}.tgz ${NAME}.docset
else
  exit 1
fi
