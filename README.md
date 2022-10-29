# zc.buildout vscode extension

This is a vscode (Visual Studio Code) extension to work with [buildout](http://docs.buildout.org/en/latest/) profiles.

It is made of two parts, a [language server](./server/README.md) that can be used standalone and a vscode extension that should also works with [Theia](https://github.com/eclipse-theia/theia) - for now it needs theia >= 1.31.0. For theia 1.31.0, running theia with `--vscode-api-version 1.67.0` command line flag is necessary.

It was developped to make it easier to work with [SlapOS](https://slapos.nexedi.com/) software profiles, but mainly as a "fun project" to learn about language server technology.
