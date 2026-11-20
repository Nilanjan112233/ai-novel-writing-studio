/** @type {import('next').NextConfig} */
const path = require('path')
const fs = require('fs')

const repositoryRoot = fs.existsSync(path.join(__dirname, '..', 'package-lock.json'))
  ? path.join(__dirname, '..')
  : __dirname

const nextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  // The repository intentionally has a root lockfile for Playwright tooling and
  // a frontend lockfile for Next.js. Declare the trace root so startup and
  // production packaging do not guess or emit a misleading workspace warning.
  outputFileTracingRoot: repositoryRoot,
}

module.exports = nextConfig
