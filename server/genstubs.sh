#!/bin/sh

mkdir -p ./stubs/zc/
echo > ./stubs/zc/__init__.pyi

for mod in \
    zc.buildout \
    zc.buildout.buildout \
    zc.buildout.configparser \
    zc.buildout.download \
    zc.buildout.easy_install \
    zc.buildout.rmtree \
    setuptools \
    setuptools.package_index \
; do
    stubgen -v -m $mod -o ./stubs/
done

# generated files where adjusted a bit.