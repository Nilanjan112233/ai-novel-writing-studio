import fs from 'fs'
import path from 'path'

const repositoryRoot = path.resolve(__dirname, '..')

/**
 * Pick the Python interpreter for the backend.
 *
 * Order: backend/.venv (if created) -> Windows "py -3.11" launcher -> python3.
 * Keeping this in one place lets the dev launcher, backend tests and the
 * Playwright setup behave the same on Windows, macOS, Linux and CI.
 */
export function pythonCommand(): { command: string; args: string[] } {
  if (process.env.NOVELFORGE_PYTHON) return { command: process.env.NOVELFORGE_PYTHON, args: [] }
  const venvPython = process.platform === 'win32'
    ? path.join(repositoryRoot, 'backend', '.venv', 'Scripts', 'python.exe')
    : path.join(repositoryRoot, 'backend', '.venv', 'bin', 'python')
  if (fs.existsSync(venvPython)) return { command: venvPython, args: [] }
  if (process.platform === 'win32') return { command: 'py', args: ['-3.11'] }
  return { command: 'python3', args: [] }
}
