// based on https://github.com/microsoft/vscode-extension-samples/tree/master/lsp-sample which
// has this copyright:
/* --------------------------------------------------------------------------------------------
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See License.txt in the project root for license information.

 * ------------------------------------------------------------------------------------------ */
import * as vscode from "vscode";
import * as child_process from "child_process";
import { workspace } from "vscode";

import {
  LanguageClient,
  LanguageClientOptions,
  Executable,
} from "vscode-languageclient/node";

let client: LanguageClient;

interface Settings {
  python: {
    executable: string;
  };
}

/**
 * Check if our package is already installed on this python.
 *
 * @param python path of the python interpreter
 */
function isExtensionInstalled(python: string): boolean {
  try {
    child_process.execFileSync(
      python,
      ["-m", "buildoutls", "--check-install"],
      {
        cwd: "/",
      }
    );
    return true;
  } catch {
    return false;
  }
}
/**
 * Check if python version looks supported.
 *
 * @param python path of the python interpreter
 */
function isPythonVersionCompatible(python: string): boolean {
  try {
    child_process.execFileSync(python, [
      "-c",
      "import sys; sys.exit(sys.version_info[:2] < (3, 9))",
    ]);
    return true;
  } catch {
    return false;
  }
}

function makeLanguageServerClient(pythonExecutable: string) {
  const serverExecutable: Executable = {
    command: pythonExecutable,
    args: ["-m", "buildoutls"].concat(
      vscode.workspace
        .getConfiguration()
        .get("zc-buildout.language.server.arguments")
    ),
  };

  let clientOptions: LanguageClientOptions = {
    documentSelector: [{ language: "zc-buildout" }],
    synchronize: {
      fileEvents: workspace.createFileSystemWatcher("**/*.{cfg,in,j2}"),
    },
  };

  return new LanguageClient(
    "zc-buildout",
    "zc.buildout Language Server",
    serverExecutable,
    clientOptions
  );
}

async function shortDelay() {
  return new Promise((resolve) => setTimeout(resolve, 1000));
}

export async function activate() {
  let settings: Settings = {
    python: {
      executable: vscode.workspace
        .getConfiguration()
        .get("zc-buildout.python.executable"),
    },
  };
  vscode.workspace.onDidChangeConfiguration(async (e) => {
    if (e.affectsConfiguration("zc-buildout.python.executable")) {
      const newPythonExecutable = vscode.workspace
        .getConfiguration()
        .get("zc-buildout.python.executable") as string;

      if (client) {
        await client.stop();
      }
      // FIXME: restarting language server does not work, after changing
      // config it's required to restart vscode
      client = makeLanguageServerClient(newPythonExecutable);
      client.start();
      vscode.window.showInformationMessage(
        `New python selected ${newPythonExecutable}`
      );
    }
  });

  let pythonExecutable = settings.python.executable;

  if (!isPythonVersionCompatible(settings.python.executable)) {
    vscode.window.showErrorMessage(
      "zc.buildout extension: Invalid python version, needs python >= 3.9"
    );
    return false;
  }

  let installationOK = isExtensionInstalled(settings.python.executable);
  if (!installationOK) {
    const venvPythonExecutable = `${__dirname}/venv/bin/python`;

    if (isExtensionInstalled(venvPythonExecutable)) {
      pythonExecutable = venvPythonExecutable;
    } else {
      let answer = await vscode.window.showErrorMessage(
        `buildout-language-server is not installed on \`${settings.python.executable}\`.
        See [documentation](https://marketplace.visualstudio.com/items?itemName=perrinjerome.vscode-zc-buildout) or install automatically in a virtual environment.`,
        "Install in a virtualenv"
      );
      if (answer === "Install in a virtualenv") {
        const terminal = vscode.window.createTerminal("zc-buildout");
        terminal.show(false);
        terminal.sendText(
          "# Installing buildout-language-server in a virtual environment.\n"
        );
        terminal.sendText(
          `${settings.python.executable} -m venv --clear "${__dirname}/venv/" && "${venvPythonExecutable}" -m pip install "${__dirname}/../../server/" -r "${__dirname}/../../server/requirements.txt"`
        );

        for (let retries = 0; retries < 60; retries++) {
          await shortDelay();
          installationOK = isExtensionInstalled(venvPythonExecutable);
          if (installationOK) {
            pythonExecutable = venvPythonExecutable;
            break;
          }
        }

        if (installationOK) {
          vscode.window.showInformationMessage(
            "zc.buildout extension: installed language server"
          );
        } else {
          vscode.window.showErrorMessage(
            "zc.buildout extension: Could not install language server"
          );
          return false;
        }
      }
    }
  }

  client = makeLanguageServerClient(pythonExecutable);
  client.start();
  return true;
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  return client.stop();
}
