import { execFileSync } from 'node:child_process';
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { build } from 'esbuild';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = resolve(root, 'dist/cmh-anesthesia/browser');
const executable = process.platform === 'win32' ? 'ngc.cmd' : 'ngc';

rmSync(resolve(root, 'out-tsc'), { recursive: true, force: true });
rmSync(output, { recursive: true, force: true });
mkdirSync(output, { recursive: true });

execFileSync(resolve(root, `node_modules/.bin/${executable}`), ['-p', 'tsconfig.app.json'], {
  cwd: root,
  stdio: 'inherit',
});

await build({
  entryPoints: [resolve(root, 'out-tsc/app/main.js')],
  outfile: resolve(output, 'main.js'),
  bundle: true,
  minify: true,
  platform: 'browser',
  target: ['es2022'],
  legalComments: 'none',
});

const index = readFileSync(resolve(root, 'src/index.html'), 'utf8')
  .replace('</head>', '    <link rel="stylesheet" href="styles.css">\n  </head>')
  .replace('</body>', '    <script type="module" src="main.js"></script>\n  </body>');
writeFileSync(resolve(output, 'index.html'), index);
cpSync(resolve(root, 'src/styles.scss'), resolve(output, 'styles.css'));
const publicDir = resolve(root, 'public');
try {
  cpSync(publicDir, output, { recursive: true });
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
}

console.log(`Built CMH Anaesthesia frontend at ${output}`);
