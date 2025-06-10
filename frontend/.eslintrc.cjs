module.exports = {
  parser: '@typescript-eslint/parser',
  plugins: ['react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:react-hooks/recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  rules: {
    'no-unused-vars': 'off',
    'no-useless-escape': 'off',
  },
};
