#!/usr/bin/env node
'use strict';
// Parse package bytes with the declared TypeScript compiler. Never load target code.
const fs = require('node:fs');
const ts = require('./require_tool.cjs')('typescript').module;
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const findings = [];
const failures = [];
const limits = ['Static intra-file analysis: arbitrary wrappers, runtime aliases and cross-file data flow are not resolved.'];
for (const input of request.files) {
  const text = input.text;
  const source = ts.createSourceFile(input.path, text, ts.ScriptTarget.Latest, true, /\.tsx$/.test(input.path) ? ts.ScriptKind.TSX : /\.jsx$/.test(input.path) ? ts.ScriptKind.JSX : /\.[cm]?ts$/.test(input.path) ? ts.ScriptKind.TS : ts.ScriptKind.JS);
  if (source.parseDiagnostics.length) failures.push({file: input.path, diagnostics: source.parseDiagnostics.map(d => ts.flattenDiagnosticMessageText(d.messageText, ' '))});
  const bindings = new Map();
  const imports = new Map();
  const decoded = new Set();
  const external = new Set();
  const snippet = n => n.getText(source).slice(0, 300);
  const location = n => source.getLineAndCharacterOfPosition(n.getStart(source)).line + 1;
  const emit = (rule, severity, node, message, evidence = {}) => findings.push({rule, severity, file: input.path, line: location(node), snippet: snippet(node), message, evidence});
  const str = n => n && (ts.isStringLiteralLike(n) || ts.isNoSubstitutionTemplateLiteral(n)) ? n.text : null;
  function symbol(node) {
    if (ts.isIdentifier(node)) return imports.get(node.text) || node.text;
    if (ts.isPropertyAccessExpression(node)) return symbol(node.expression) + '.' + node.name.text;
    if (ts.isElementAccessExpression(node) && str(node.argumentExpression)) return symbol(node.expression) + '.' + str(node.argumentExpression);
    if (ts.isCallExpression(node) && symbol(node.expression) === 'require' && str(node.arguments[0])) return str(node.arguments[0]).replace(/^node:/, '');
    return '';
  }
  function contains(node, pred) {
    if (!node) return false;
    if (pred(node)) return true;
    let yes = false;
    ts.forEachChild(node, child => { if (contains(child, pred)) yes = true; });
    return yes;
  }
  function isDecoded(node) {
    return contains(node, n => ts.isIdentifier(n) && decoded.has(n.text) || ts.isCallExpression(n) && (/^(atob|Buffer\.from|buffer\.Buffer\.from)$/.test(symbol(n.expression)) && (symbol(n.expression) === 'atob' || n.arguments.some(a => str(a) === 'base64' || str(a) === 'hex'))));
  }
  function isExternal(node) {
    return contains(node, n => ts.isIdentifier(n) && external.has(n.text) || ts.isPropertyAccessExpression(n) && /^process\.(env|argv)/.test(symbol(n)) || ts.isCallExpression(n) && /^(fetch|https\.(get|request)|http\.(get|request)|fs\.(readFileSync|readFile))$/.test(symbol(n.expression)));
  }
  function setup(node) {
    if (ts.isImportDeclaration(node) && node.importClause && str(node.moduleSpecifier)) {
      const mod = str(node.moduleSpecifier).replace(/^node:/, '');
      if (node.importClause.name) imports.set(node.importClause.name.text, mod);
      const named = node.importClause.namedBindings;
      if (named && ts.isNamespaceImport(named)) imports.set(named.name.text, mod);
      if (named && ts.isNamedImports(named)) for (const entry of named.elements) imports.set(entry.name.text, mod + '.' + (entry.propertyName || entry.name).text);
    }
    if (ts.isVariableDeclaration(node) && node.initializer) {
      if (ts.isIdentifier(node.name)) {
        bindings.set(node.name.text, node.initializer);
        const resolved = symbol(node.initializer);
        if (resolved) imports.set(node.name.text, resolved);
      } else if (ts.isObjectBindingPattern(node.name)) {
        const mod = symbol(node.initializer);
        if (mod) for (const entry of node.name.elements) if (ts.isIdentifier(entry.name)) imports.set(entry.name.text, mod + '.' + (entry.propertyName || entry.name).text);
      }
    }
    ts.forEachChild(node, setup);
  }
  setup(source);
  for (let round = 0; round <= bindings.size; round++) {
    const count = decoded.size + external.size;
    for (const [name, expr] of bindings) {
      if (isDecoded(expr)) decoded.add(name);
      if (isExternal(expr)) external.add(name);
    }
    if (count === decoded.size + external.size) break;
  }
  function walk(node) {
    if (ts.isCallExpression(node) || ts.isNewExpression(node)) {
      const name = symbol(node.expression);
      const args = node.arguments || [];
      const evaluation = /^(eval|Function|vm\.(runInNewContext|runInContext|runInThisContext|compileFunction|Script))$/.test(name);
      const loader = name === 'require' || node.expression.kind === ts.SyntaxKind.ImportKeyword;
      if (evaluation) emit('dynamic-eval', args.some(isExternal) || args.some(isDecoded) ? 'BLOCK' : 'WARN', node, 'Dynamic code evaluation', {callee: name, demonstratedInputFlow: args.some(isExternal) || args.some(isDecoded)});
      if ((evaluation || loader) && args.some(isDecoded)) emit('decoded-execution', 'BLOCK', node, 'Decoded bytes reach code execution or dynamic loading', {callee: name});
      const processCall = /^child_process\.(exec|execSync|spawn|spawnSync|execFile|execFileSync)$/.test(name);
      const network = /^(fetch|https\.(get|request)|http\.(get|request))$/.test(name);
      const sensitive = /^fs\.(readFile|readFileSync)$/.test(name) && args.some(a => /(?:\.npmrc|\.ssh|\.aws|credentials)/i.test(str(a) || snippet(a)));
      if (processCall || network || sensitive) {
        let parent = node.parent, top = true;
        while (parent && parent !== source) { if (ts.isFunctionLike(parent)) top = false; parent = parent.parent; }
        const dangerous = processCall && (args.some(isExternal) || args.some(isDecoded) || args.some(a => /(?:curl|wget).*(?:\||;|&&).*(?:sh|bash|node)|rm\s+-rf/.test(str(a) || '')));
        emit('lifecycle-effects', dangerous ? 'BLOCK' : 'WARN', node, processCall ? 'Process execution needs lifecycle/import review' : sensitive ? 'Sensitive file access needs review' : 'Network access needs lifecycle/import review', {callee: name, moduleScope: top, demonstratedDangerousChain: dangerous});
      }
    }
    ts.forEachChild(node, walk);
  }
  walk(source);
}
process.stdout.write(JSON.stringify({findings, failures, limitations: limits, parserVersion: ts.version}));
