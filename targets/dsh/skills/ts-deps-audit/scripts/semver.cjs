#!/usr/bin/env node
'use strict';
const semver = require('./require_tool.cjs')('semver').module;
const fs = require('node:fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const output = input.map(item => {
  if (item.op === 'satisfies') {
    if (!semver.validRange(item.range) || !semver.valid(item.version)) throw Error('Invalid semver range or version');
    return semver.satisfies(item.version, item.range);
  }
  if (item.op === 'select') {
    if (!semver.validRange(item.range)) throw Error('Unsupported candidate constraint: ' + item.range);
    return semver.maxSatisfying(item.versions.filter(v => semver.valid(v) && !semver.prerelease(v)), item.range);
  }
  if (item.op === 'patch') {
    return semver.valid(item.old) && semver.valid(item.new) && semver.major(item.old) === semver.major(item.new) && semver.minor(item.old) === semver.minor(item.new) && semver.gt(item.new, item.old);
  }
  throw Error('Unknown semver operation');
});
process.stdout.write(JSON.stringify(output));
