'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const pinned = { typescript: '5.9.3', semver: '7.7.2' };
module.exports = function tool(name) {
  const roots = [process.env.TS_AUDIT_TOOLING, __dirname, process.env.TS_AUDIT_ROOT].filter(Boolean);
  for (const start of roots) {
    let root = path.resolve(start);
    while (true) {
      const manifest = path.join(root, 'package.json');
      if (fs.existsSync(manifest)) {
        const data = JSON.parse(fs.readFileSync(manifest, 'utf8'));
        if (data.dependencies?.[name] || data.devDependencies?.[name]) {
          try {
            const loader = createRequire(manifest);
            const packagePath = loader.resolve(name + '/package.json');
            const installed = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
            if (installed.version === pinned[name]) return { module: loader(name), packagePath, entry: loader.resolve(name) };
          } catch { /* Try another explicitly declared tooling root. */ }
        }
      }
      const parent = path.dirname(root);
      if (parent === root) break;
      root = parent;
    }
  }
  throw Error(`Required parser ${name}@${pinned[name]} is unavailable. Set TS_AUDIT_TOOLING to the explicitly provisioned tooling directory. The auditor never installs packages.`);
};
if (require.main === module) {
  const data = {};
  for (const name of Object.keys(pinned)) {
    const loaded = module.exports(name);
    data[name] = { packagePath: loaded.packagePath, entry: loaded.entry, version: pinned[name] };
  }
  process.stdout.write(JSON.stringify(data));
}
