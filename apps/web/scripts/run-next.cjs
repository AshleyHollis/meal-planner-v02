const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const [, , command, fallbackDistDir, ...args] = process.argv;

if (!command) {
  console.error('Missing Next.js command.');
  process.exit(1);
}

const distDir = (process.env.NEXT_DIST_DIR || fallbackDistDir || '.next').trim() || '.next';
const resolvedDistDir = path.resolve(process.cwd(), distDir);

if (command === 'dev' || command === 'build') {
  fs.rmSync(resolvedDistDir, { recursive: true, force: true });
}

const nextCli = require.resolve('next/dist/bin/next');
const result = spawnSync(process.execPath, [nextCli, command, ...args], {
  stdio: 'inherit',
  env: {
    ...process.env,
    NEXT_DIST_DIR: distDir,
  },
});

if (result.error) {
  console.error(result.error);
  process.exit(1);
}

process.exit(result.status ?? 0);
