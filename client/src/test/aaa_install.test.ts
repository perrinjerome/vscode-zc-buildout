// based on https://github.com/microsoft/vscode-extension-samples/tree/master/lsp-sample which
// has this copyright:
/* --------------------------------------------------------------------------------------------
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See License.txt in the project root for license information.
 * ------------------------------------------------------------------------------------------ */

import * as vscode from "vscode";
import * as assert from "assert";
import { getDocUri, activateExtension, sleep } from "./helper";
import * as child_process from "child_process";
import * as sinon from "sinon";

/**
 * This test verifies the installation process of the extension, it has to run first.
 */
describe("Installation", () => {
  var showQuickPickMock: sinon.SinonStub,
    showErrorMessageMock: sinon.SinonStub,
    showInformationMessage: sinon.SinonStub;

  before(() => {
    try {
      // uninstall if already installed
      child_process.execFileSync("python3", [
        "-m",
        "pip",
        "uninstall",
        "-y",
        "zc.buildout.languageserver"
      ]);
    } catch {}

    vscode.window.showQuickPick = showQuickPickMock = (sinon.stub(
      vscode.window,
      "showQuickPick"
    ) as any).resolves("Yes");

    showErrorMessageMock = sinon.stub(vscode.window, "showErrorMessage");

    showInformationMessage = sinon.stub(
      vscode.window,
      "showInformationMessage"
    );
  });
  after(() => {
    showQuickPickMock.restore();
    showErrorMessageMock.restore();
    showInformationMessage.restore();
  });

  it("First install language server", async () => {
    const docUri = getDocUri("completions/sections.cfg");

    showQuickPickMock.resolves("Yes");

    await activateExtension(docUri);

    for (let retries = 0; retries < 10; retries++) {
      if (showQuickPickMock.called) break;

      sleep(1000);
    }
    assert(showQuickPickMock.calledOnce);
    if (showErrorMessageMock.called) {
      throw new Error(
        JSON.stringify(showErrorMessageMock.getCalls(), null, "  ")
      );
    }
    assert(showErrorMessageMock.notCalled);
    assert(
      showInformationMessage.calledWith(
        "zc.buildout extension: installed language server"
      )
    );
    child_process.execFileSync("python3", [
      "-m",
      "buildoutls",
      "--check-install"
    ]);
  });
});
