// based on https://github.com/microsoft/vscode-extension-samples/tree/master/lsp-sample which
// has this copyright:
/* --------------------------------------------------------------------------------------------
 * Copyright (c) Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See License.txt in the project root for license information.
 * ------------------------------------------------------------------------------------------ */

import * as vscode from "vscode";
import * as assert from "assert";
import { getDocUri, activateExtension, sleep } from "./helper";

describe("Diagnostics", () => {
  const docUri = getDocUri("broken/reference.cfg");

  it("Diagnoses non existent options and sections.", async () => {
    await testDiagnostics(docUri, [
      {
        message: "Section `missing_section` does not exist.",
        range: toRange(1, 12, 1, 27),
        severity: vscode.DiagnosticSeverity.Error,
        source: "buildout"
      },
      {
        message: "Option `missing_option` does not exist in `section2`.",
        range: toRange(2, 21, 2, 35),
        severity: vscode.DiagnosticSeverity.Warning,
        source: "buildout"
      }
    ]);
  });
});

function toRange(sLine: number, sChar: number, eLine: number, eChar: number) {
  const start = new vscode.Position(sLine, sChar);
  const end = new vscode.Position(eLine, eChar);
  return new vscode.Range(start, end);
}

async function testDiagnostics(
  docUri: vscode.Uri,
  expectedDiagnostics: vscode.Diagnostic[]
) {
  await activateExtension(docUri);

  let actualDiagnostics;
  for (var i = 0; i <= 10; i++) {
    actualDiagnostics = vscode.languages.getDiagnostics(docUri);
    if (actualDiagnostics.length) {
      break;
    }
    console.log(
      `${new Date()}: did not get diagnostics, retrying in 2 seconds`
    );
    await sleep(2000);
  }

  assert.equal(actualDiagnostics.length, expectedDiagnostics.length);

  expectedDiagnostics.forEach((expectedDiagnostic, i) => {
    const actualDiagnostic = actualDiagnostics[i];
    assert.equal(actualDiagnostic.message, expectedDiagnostic.message);
    assert.deepEqual(actualDiagnostic.range, expectedDiagnostic.range);
    assert.equal(actualDiagnostic.severity, expectedDiagnostic.severity);
    assert.equal(actualDiagnostic.source, expectedDiagnostic.source);
  });
}
