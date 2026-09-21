import js from "@eslint/js"
import vitest from "@vitest/eslint-plugin"
import importX from "eslint-plugin-import-x"
import jsxA11y from "eslint-plugin-jsx-a11y"
import reactHooks from "eslint-plugin-react-hooks"
import sonarjs from "eslint-plugin-sonarjs"
import testingLibrary from "eslint-plugin-testing-library"
import globals from "globals"
import tseslint from "typescript-eslint"

const FS_IGNORES = [
  "**/dist/**",
  "**/node_modules/**",
  "**/coverage/**",
  "**/.turbo/**",
  "**/.venv/**",
  "packages/contracts/src/generated/**",
]

/**
 * FSD dependency direction: a layer may only import layers below itself.
 * Enforced with the built-in no-restricted-imports rule, layer by layer.
 */
const fsdLayers = [
  { layer: "shared", forbidden: ["app", "pages", "widgets", "features", "entities"] },
  { layer: "entities", forbidden: ["app", "pages", "widgets", "features"] },
  { layer: "features", forbidden: ["app", "pages", "widgets"] },
  { layer: "widgets", forbidden: ["app", "pages"] },
  { layer: "pages", forbidden: ["app"] },
]

const fsdRules = fsdLayers.map(({ layer, forbidden }) => ({
  files: [`apps/web/src/${layer}/**/*.{ts,tsx}`],
  rules: {
    "no-restricted-imports": [
      "error",
      {
        patterns: forbidden.map((target) => ({
          group: [`@/${target}/*`],
          message: `FSD: "${layer}" must not import from "${target}" (dependency direction is app > pages > widgets > features > entities > shared).`,
        })),
      },
    ],
  },
}))

export default tseslint.config(
  { ignores: FS_IGNORES },
  { ignores: ["eslint.config.mjs"] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: {
          allowDefaultProject: ["*.config.ts", "*.config.mjs"],
        },
        tsconfigRootDir: import.meta.dirname,
      },
      globals: { ...globals.browser, ...globals.node },
    },
    plugins: {
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      sonarjs,
      "import-x": importX,
    },
    settings: {
      "import-x/resolver": { typescript: true },
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.flatConfigs.recommended.rules,
      ...sonarjs.configs.recommended.rules,

      "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports", fixStyle: "inline-type-imports" },
      ],
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/restrict-template-expressions": [
        "error",
        { allowNumber: true, allowBoolean: true },
      ],
      "@typescript-eslint/no-misused-promises": [
        "error",
        { checksVoidReturn: { attributes: false } },
      ],
      "import-x/no-cycle": "error",
      // Import ordering is Biome's job (assist/actions/source/organizeImports).
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "sonarjs/cognitive-complexity": ["error", 25],
      // Props are never mutated in this codebase; adding Readonly<> everywhere is noise.
      "sonarjs/prefer-read-only-props": "off",
      // React event handlers routinely return void expressions (setState, navigate).
      "@typescript-eslint/no-confusing-void-expression": "off",
    },
  },
  ...fsdRules,
  {
    files: ["**/*.test.{ts,tsx}", "**/test/**/*.{ts,tsx}", "**/setup-tests.ts"],
    plugins: { vitest, "testing-library": testingLibrary },
    languageOptions: {
      globals: { ...vitest.environments.env.globals },
    },
    rules: {
      ...vitest.configs.recommended.rules,
      ...testingLibrary.configs["flat/react"].rules,
      "@typescript-eslint/no-non-null-assertion": "off",
      "@typescript-eslint/unbound-method": "off",
      "sonarjs/no-duplicate-string": "off",
      // SVG internals and layout regions have no accessible query surface.
      "testing-library/no-node-access": "off",
      "testing-library/no-container": "off",
      "vitest/expect-expect": [
        "error",
        { assertFunctionNames: ["expect", "expectNoA11yViolations"] },
      ],
    },
  },
  {
    files: ["**/setup-tests.ts", "**/test/**/*.{ts,tsx}"],
    rules: {
      // Test setup intentionally stubs browser APIs that the DOM types declare always present.
      "@typescript-eslint/no-unnecessary-condition": "off",
      "@typescript-eslint/no-empty-function": "off",
      "@typescript-eslint/no-unnecessary-type-assertion": "off",
      "@typescript-eslint/no-confusing-void-expression": "off",
      "testing-library/no-manual-cleanup": "off",
    },
  },
  {
    files: ["**/*.config.{ts,mjs,js}", "**/*.d.ts"],
    rules: {
      "@typescript-eslint/no-unsafe-assignment": "off",
      "import-x/no-default-export": "off",
    },
  },
)
