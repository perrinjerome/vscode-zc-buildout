# zc.buildout vscode extension

This is a vscode (Visual Studio Code) extension to work with [buildout](http://docs.buildout.org/en/latest/) profiles.

It is made of two parts, a [language server](./server/README.md) that can be used standalone and a vscode extension that should also works with [Theia](https://github.com/eclipse-theia/theia).

It was developped to make it easier to work with [SlapOS](https://slapos.nexedi.com/) software profiles, but mainly as a "fun project" to learn about language server technology.

## Installation

The vscode extension expects that the language server is already installed on the configured python interpreter ( by default `python3` ), but if it's not the case at startup it offers to install the extension in a virtual environment created automatically within the extension installation directory.
