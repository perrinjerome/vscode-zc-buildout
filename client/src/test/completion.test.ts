// based on https://github.com/microsoft/vscode-extension-samples/tree/master/lsp-sample which
// has this copyright:
/* --------------------------------------------------------------------------------------------
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See License.txt in the project root for license information.
 * ------------------------------------------------------------------------------------------ */

import * as vscode from "vscode";
import * as assert from "assert";
import { getDocUri, activateExtension, sleep } from "./helper";
import { describe, it } from "mocha";

describe("Completions", () => {
  const docUri = getDocUri("completions/sections.cfg");

  it("Completes other sections", async () => {
    await testCompletion(docUri, new vscode.Position(4, 32), {
      items: [
        { label: "buildout", kind: vscode.CompletionItemKind.Class },
        { label: "section1", kind: vscode.CompletionItemKind.Class },
        { label: "section2", kind: vscode.CompletionItemKind.Class },
        { label: "section3", kind: vscode.CompletionItemKind.Class },
        { label: "xsection4", kind: vscode.CompletionItemKind.Class },
      ],
    });

    it("Completes other sections options", async () => {
      await testCompletion(docUri, new vscode.Position(14, 21), {
        items: [
          { label: "recipe", kind: vscode.CompletionItemKind.Interface },
          { label: "option4", kind: vscode.CompletionItemKind.Interface },
        ],
      });
    });
  });
});

async function testCompletion(
  docUri: vscode.Uri,
  position: vscode.Position,
  expectedCompletionList: vscode.CompletionList
) {
  await activateExtension(docUri);

  // Executing the command `vscode.executeCompletionItemProvider` to simulate triggering completion
  let actualCompletionList;
  for (var i = 0; i <= 10; i++) {
    actualCompletionList = (await vscode.commands.executeCommand(
      "vscode.executeCompletionItemProvider",
      docUri,
      position
    )) as vscode.CompletionList;

    if (actualCompletionList.items.length) {
      break;
    }
    console.log(
      `${new Date()}: did not get completions, retrying in 2 seconds`
    );
    await sleep(2000);
  }

  assert.equal(
    actualCompletionList.items.length,
    expectedCompletionList.items.length
  );
  expectedCompletionList.items.forEach((expectedItem, i) => {
    const actualItem = actualCompletionList.items[i];
    assert.equal(actualItem.label, expectedItem.label);
    assert.equal(actualItem.kind, expectedItem.kind);
  });
}
