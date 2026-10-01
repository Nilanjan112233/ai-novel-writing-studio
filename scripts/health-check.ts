#!/usr/bin/env tsx
/**
 * Health Check Utility
 * 
 * This script checks the health of the NovelForge application services:
 * - MongoDB connection
 * - Backend API health endpoint
 * - Frontend availability
 * 
 * Usage: npx tsx scripts/health-check.ts
 */

import http from 'http';
import { MongoClient } from 'mongodb';
import fs from 'fs';

let detectedBackendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
let detectedFrontendUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
try {
  if (!process.env.BACKEND_URL && fs.existsSync('.novelforge-ports.json')) {
    const ports = JSON.parse(fs.readFileSync('.novelforge-ports.json', 'utf-8'));
    detectedBackendUrl = `http://localhost:${ports.backendPort || 8000}`;
    detectedFrontendUrl = `http://localhost:${ports.frontendPort || 3000}`;
  }
} catch {
  // Fall back to defaults when the dev-port hint is unavailable.
}

const MONGODB_URL = process.env.MONGODB_URL || 'mongodb://localhost:27017';
const BACKEND_URL = detectedBackendUrl;
const FRONTEND_URL = detectedFrontendUrl;

interface HealthCheckResult {
  service: string;
  status: 'healthy' | 'unhealthy';
  message: string;
  responseTime?: number;
}

interface OperationalReadiness {
  status: 'ready' | 'offline_ready' | 'blocked';
  summary: string;
  app_version: string;
  checks: Record<string, { status: string; explanation: string }>;
}

function checkUrl(url: string, serviceName: string): Promise<HealthCheckResult> {
  return new Promise((resolve) => {
    const start = Date.now();
    
    http.get(url, (res) => {
      const responseTime = Date.now() - start;
      
      if (res.statusCode === 200) {
        resolve({
          service: serviceName,
          status: 'healthy',
          message: `Responded with ${res.statusCode}`,
          responseTime
        });
      } else {
        resolve({
          service: serviceName,
          status: 'unhealthy',
          message: `Responded with ${res.statusCode}`,
          responseTime
        });
      }
    }).on('error', (error) => {
      const responseTime = Date.now() - start;
      resolve({
        service: serviceName,
        status: 'unhealthy',
        message: error.message || `${serviceName} is not running or is not reachable`,
        responseTime
      });
    });
  });
}

async function checkMongoDB(): Promise<HealthCheckResult> {
  const start = Date.now();
  
  try {
    const client = new MongoClient(MONGODB_URL);
    await client.connect();
    await client.db('admin').command({ ping: 1 });
    await client.close();
    
    const responseTime = Date.now() - start;
    
    return {
      service: 'MongoDB',
      status: 'healthy',
      message: 'Connection successful',
      responseTime
    };
  } catch (error: any) {
    const responseTime = Date.now() - start;
    
    return {
      service: 'MongoDB',
      status: 'unhealthy',
      message: error.message || 'MongoDB is not running or is not reachable. Existing data has not been changed.',
      responseTime
    };
  }
}

async function main() {
  console.log('NovelForge Private Beta readiness\n');
  
  const results: HealthCheckResult[] = [];
  
  // Check MongoDB
  console.log('Checking local project storage...');
  const mongoResult = await checkMongoDB();
  results.push(mongoResult);
  console.log(`  ${mongoResult.status === 'healthy' ? 'READY' : 'NEEDS ATTENTION'} Project storage: ${mongoResult.message} (${mongoResult.responseTime}ms)\n`);
  
  // Check Backend API
  console.log('Checking Backend API...');
  const backendResult = await checkUrl(`${BACKEND_URL}/health`, 'Backend API');
  results.push(backendResult);
  console.log(`  ${backendResult.status === 'healthy' ? 'READY' : 'NEEDS ATTENTION'} NovelForge service: ${backendResult.message || 'not reachable'} (${backendResult.responseTime}ms)\n`);
  
  // Check Frontend
  console.log('Checking Frontend...');
  const frontendResult = await checkUrl(FRONTEND_URL, 'Frontend');
  results.push(frontendResult);
  console.log(`  ${frontendResult.status === 'healthy' ? 'READY' : 'NEEDS ATTENTION'} Author workspace: ${frontendResult.message || 'not reachable'} (${frontendResult.responseTime}ms)\n`);

  if (backendResult.status === 'healthy') {
    try {
      const response = await fetch(`${BACKEND_URL}/api/operations/readiness`);
      if (response.ok) {
        const readiness = await response.json() as OperationalReadiness;
        console.log(`${readiness.summary} (${readiness.app_version})`);
        for (const [name, check] of Object.entries(readiness.checks)) {
          console.log(`  - ${name}: ${check.status} — ${check.explanation}`);
        }
        if (readiness.status === 'blocked') process.exitCode = 1;
      }
    } catch {
      console.log('  Operational details are not available yet. Retry after startup finishes.');
    }
  }
  
  // Summary
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  const healthyCount = results.filter(r => r.status === 'healthy').length;
  const totalCount = results.length;
  
  if (healthyCount === totalCount) {
    console.log(`All local services are reachable (${healthyCount}/${totalCount}).`);
    process.exit(process.exitCode || 0);
  } else {
    console.log(`NovelForge is not fully started (${healthyCount}/${totalCount} services reachable).`);
    console.log('Your saved work has not been changed. Start MongoDB or run npm run beta:start, then check again.');
    process.exit(1);
  }
}

main().catch(error => {
  console.error('Health check failed:', error);
  process.exit(1);
});
