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
import { describe, before, after, it } from "mocha";

/**
 * This test verifies the installation process of the extension, it has to run first.
 */
describe("Installation", () => {
  var showQuickPickMock: sinon.SinonStub,
    showErrorMessageMock: sinon.SinonStub,
    showInformationMessage: sinon.SinonStub;

  before(() => {
    vscode.window.showErrorMessage = showErrorMessageMock = sinon.stub(
      vscode.window,
      "showErrorMessage"
    );

    showInformationMessage = sinon.stub(
      vscode.window,
      "showInformationMessage"
    );
  });
  after(() => {
    showErrorMessageMock.restore();
    showInformationMessage.restore();
  });

  it("First install language server", async () => {
    const docUri = getDocUri("completions/sections.cfg");

    showErrorMessageMock.resolves("Install in a virtualenv");

    await activateExtension(docUri);

    for (let retries = 0; retries < 30; retries++) {
      if (showErrorMessageMock.called) break;

      await sleep(1000);
    }
    assert.strictEqual(showErrorMessageMock.getCalls().length, 1);
    assert(
      showInformationMessage.calledWith(
        "zc.buildout extension: installed language server"
      )
    );
  });
});
