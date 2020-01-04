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
  Executable
} from "vscode-languageclient";

let client: LanguageClient;

interface Settings {
  python: {
    executable: string;
  };
}

/**
 * Check if our egg is already installed on this python.
 *
 * @param python path of the python interpreter
 */
function isExtensionInstalled(python: string): boolean {
  try {
    child_process.execFileSync(python, ["-m", "buildoutls", "--check-install"]);
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
      "import sys; sys.exit(sys.version_info[:2] < (3, 6))"
    ]);
    return true;
  } catch {
    return false;
  }
}

async function shortDelay() {
  return new Promise(resolve => setTimeout(resolve, 1000));
}

export async function activate() {
  let settings: Settings = {
    python: {
      executable: vscode.workspace
        .getConfiguration()
        .get("zc-buildout.python.executable")
    }
  };
  vscode.workspace.onDidChangeConfiguration(e => {
    if (e.affectsConfiguration("zc-buildout.python.executable")) {
      vscode.window.showInformationMessage(
        "New python selected (" +
          vscode.workspace
            .getConfiguration()
            .get("zc-buildout.python.executable") +
          "): needs application restart"
      );
    }
  });

  let serverExecutable: Executable = {
    command: settings.python.executable,
    args: ["-m", "buildoutls"].concat(
      vscode.workspace
        .getConfiguration()
        .get("zc-buildout.language.server.arguments")
    )
  };

  // Options to control the language client
  let clientOptions: LanguageClientOptions = {
    // Register the server for buildout files
    documentSelector: [{ language: "zc.buildout" }],
    synchronize: {
      fileEvents: workspace.createFileSystemWatcher("**/*.{cfg,in,j2}")
    }
  };

  client = new LanguageClient(
    "zc-buildout",
    "zc.buildout Language Server",
    serverExecutable,
    clientOptions
  );

  if (!isPythonVersionCompatible(settings.python.executable)) {
    vscode.window.showErrorMessage(
      "zc.buildout extension: Invalid python version, needs python >= 3.6"
    );
    return false;
  }

  // Check if we are properly installed on the selected python
  let installationOK = isExtensionInstalled(settings.python.executable);
  if (!installationOK) {
    let answer = await vscode.window.showQuickPick(["Yes", "No"], {
      placeHolder: `buildout-language-server is not installed on ${settings.python.executable}. Do you want to install it now ?`
    });
    if (answer !== "Yes") {
      return false;
    }

    const terminal = vscode.window.createTerminal("zc-buildout");
    terminal.show(false);
    terminal.sendText(
      "# Install buildout-language-server on selected python.\n"
    );
    terminal.sendText(
      `${settings.python.executable} -m pip install --user -e "${__dirname}/../../server/"
`
    );
    for (let retries = 0; retries < 5; retries++) {
      await shortDelay();
      installationOK = isExtensionInstalled(settings.python.executable);
    }
    if (installationOK) {
      vscode.window.showInformationMessage(
        "zc.buildout extension: installed language server"
      );
    } else {
      vscode.window.showErrorMessage(
        "zc.buildout extension: Could not install language server"
      );
    }
    client.start();
  } else {
    client.start();
  }
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  return client.stop();
}
