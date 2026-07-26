// ESLint was never actually configured in this project before now (no
// eslint/eslint-config-next dependency existed, no config file) — `npm run
// lint` would hang CI forever on the interactive first-run setup prompt.
// Standard Next.js flat config, non-interactive.
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;
