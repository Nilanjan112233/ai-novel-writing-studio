import { spawn } from 'child_process'
import * as net from 'net'
import http from 'http'
import fs from 'fs'
import { pythonCommand } from './python'

const FRONTEND_PORT = 3000
const DEFAULT_BACKEND_PORT = 8000
let backendPort = DEFAULT_BACKEND_PORT

function checkPort(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.listen(port, () => {
      server.close()
      resolve(true) // Port is available
    })
    server.on('error', () => {
      resolve(false) // Port is in use
    })
  })
}

function probeHttp(port: number): Promise<number | null> {
  return new Promise((resolve) => {
    const request = http.get(`http://localhost:${port}/api/settings/models`, (response) => {
      response.resume()
      resolve(response.statusCode ?? null)
    })
    request.on('error', () => resolve(null))
    request.setTimeout(1000, () => {
      request.destroy()
      resolve(null)
    })
  })
}

async function findBackendPort(startPort: number): Promise<number> {
  for (let port = startPort; port < startPort + 20; port += 1) {
    const available = await checkPort(port)
    const existingStatus = await probeHttp(port)
    if (available && existingStatus === null) return port
  }
  throw new Error(`No backend port available starting at ${startPort}`)
}

async function setupPorts() {
  console.log('[dev] Checking ports...')

  const frontendAvailable = await checkPort(FRONTEND_PORT)
  const backendAvailable = await checkPort(DEFAULT_BACKEND_PORT)

  if (!frontendAvailable) {
    throw new Error(
      `Port ${FRONTEND_PORT} is already in use. NovelForge did not stop that process. ` +
      'Close the owning application or use the supported beta launcher.'
    )
  }

  if (!backendAvailable) {
    throw new Error(
      `Port ${DEFAULT_BACKEND_PORT} is already in use. NovelForge did not stop that process. ` +
      'Run npm run health to determine whether NovelForge is already running.'
    )
  }

  backendPort = await findBackendPort(DEFAULT_BACKEND_PORT)
  if (backendPort !== DEFAULT_BACKEND_PORT) {
    console.log(`[dev] Backend port ${DEFAULT_BACKEND_PORT} is still occupied; using ${backendPort}`)
  }

  fs.writeFileSync('.novelforge-ports.json', JSON.stringify({ frontendPort: FRONTEND_PORT, backendPort }, null, 2))
  console.log('[dev] Ports are ready')
}

function startBackend() {
  console.log('[dev] Starting backend...')
  const python = pythonCommand()
  const proc = spawn(python.command, [...python.args, '-m', 'uvicorn', 'main:app', '--reload', '--host', '127.0.0.1', '--port', String(backendPort)], {
    cwd: 'backend'
  })

  proc.stdout.on('data', (data) => {
    console.log('[backend]', data.toString().trim())
  })

  proc.stderr.on('data', (data) => {
    console.error('[backend]', data.toString().trim())
  })

  proc.on('close', (code) => {
    console.log(`[dev] Backend exited with code ${code}`)
  })

  return proc
}

function startFrontend() {
  console.log('[dev] Starting frontend...')
  const command = process.platform === 'win32' ? 'cmd.exe' : 'npm'
  const args = process.platform === 'win32'
    ? ['/d', '/s', '/c', 'npm', 'run', 'dev']
    : ['run', 'dev']
  const proc = spawn(command, args, {
    cwd: 'frontend',
    env: {
      ...process.env,
      NEXT_PUBLIC_API_URL: `http://localhost:${backendPort}`,
    },
  })

  proc.stdout.on('data', (data) => {
    console.log('[frontend]', data.toString().trim())
  })

  proc.stderr.on('data', (data) => {
    console.error('[frontend]', data.toString().trim())
  })

  proc.on('close', (code) => {
    console.log(`[dev] Frontend exited with code ${code}`)
  })

  return proc
}

async function main() {
  console.log('[dev] NovelForge Development Server')
  console.log('[dev] Starting MongoDB (ensure MongoDB is running on localhost:27017)')
  
  await setupPorts()

  const backendProc = startBackend()
  const frontendProc = startFrontend()

  console.log('[dev] Servers started')
  console.log('[dev] Frontend: http://localhost:3000')
  console.log(`[dev] Backend API: http://localhost:${backendPort}`)
  console.log(`[dev] API Docs: http://localhost:${backendPort}/docs`)
  console.log('[dev] Press Ctrl+C to stop')

  const cleanup = () => {
    console.log('[dev] Shutting down...')
    backendProc.kill()
    frontendProc.kill()
    process.exit(0)
  }

  process.on('SIGINT', cleanup)
  process.on('SIGTERM', cleanup)

  // Wait for either process to exit
  const waitForExit = (proc: any, name: string) => {
    return new Promise<void>((resolve) => {
      proc.on('close', (code: number) => {
        console.log(`[dev] ${name} exited with code ${code}`)
        resolve()
      })
    })
  }

  // Wait for either process to exit unexpectedly
  await Promise.race([
    waitForExit(backendProc, 'Backend'),
    waitForExit(frontendProc, 'Frontend')
  ])

  // If we get here, one process exited unexpectedly
  console.log('[dev] One process exited unexpectedly, shutting down...')
  cleanup()
}

main().catch((error) => {
  console.error('[dev] Error:', error)
  process.exit(1)
})
