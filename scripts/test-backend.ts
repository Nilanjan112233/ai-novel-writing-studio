import { spawnSync } from 'child_process'
import path from 'path'
import { pythonCommand } from './python'

// Run the backend pytest suite with the same interpreter the dev launcher uses.
// Extra arguments are passed through: npm run test:backend -- -k drafting
const python = pythonCommand()
const result = spawnSync(
  python.command,
  [...python.args, '-m', 'pytest', ...process.argv.slice(2)],
  { cwd: path.resolve(__dirname, '..', 'backend'), stdio: 'inherit' },
)
if (result.error) {
  console.error(`[test:backend] Could not start Python (${python.command}): ${result.error.message}`)
  process.exit(1)
}
process.exit(result.status ?? 1)
