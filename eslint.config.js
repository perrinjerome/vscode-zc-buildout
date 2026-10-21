const { defineConfig, globalIgnores } = require("eslint/config");

const tsParser = require("@typescript-eslint/parser");
const js = require("@eslint/js");

const { FlatCompat } = require("@eslint/eslintrc");

const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: js.configs.recommended,
  allConfig: js.configs.all,
});

module.exports = defineConfig([
  {
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2018,
      sourceType: "module",
      parserOptions: {},
    },

    extends: compat.extends("plugin:prettier/recommended"),
  },
  globalIgnores([
    "**/node_modules",
    "**/node_modules",
    "**/lib",
    "**/build",
    "**/static",
  ]),
]);
