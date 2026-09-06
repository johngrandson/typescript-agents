#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

function git(args) {
  const result = spawnSync("git", args, {
    encoding: "utf8",
  });
  if (result.error) throw result.error;
  return result;
}

function localConfig(args) {
  return git(["config", "--local", ...args]);
}

function requireSuccess(result, operation) {
  if (result.status !== 0) {
    throw new Error(`${operation}: ${result.stderr.trim() || "Git configuration failed"}`);
  }
}

function restoreLocal(previous) {
  if (previous.length === 0) {
    const removed = localConfig(["--unset-all", "core.hooksPath"]);
    if (removed.status !== 5) requireSuccess(removed, "Restore inherited hook path");
    return;
  }
  requireSuccess(localConfig(["--replace-all", "core.hooksPath", previous[0]]), "Restore previous local hook path");
  for (const value of previous.slice(1)) {
    requireSuccess(localConfig(["--add", "core.hooksPath", value]), "Restore duplicate local hook path");
  }
}

function installHooks() {
  const configured = localConfig(["--null", "--get-all", "core.hooksPath"]);
  if (configured.status !== 0 && configured.status !== 1) {
    requireSuccess(configured, "Read local hook configuration");
  }
  const previous = configured.status === 0
    ? configured.stdout.split("\0").slice(0, -1)
    : [];
  // Custom local paths remain untouched, including mixed duplicate entries.
  const migrate = previous.length > 0 && previous.every(
    (value) => value === ".husky/_" || value === ".husky",
  );
  let changed = false;
  try {
    if (migrate) {
      requireSuccess(localConfig(["--unset-all", "core.hooksPath"]), "Remove legacy local hook path");
      changed = true;
    }

    const effective = git(["config", "--show-scope", "--null", "--get", "core.hooksPath"]);
    if (effective.status !== 0 && effective.status !== 1) {
      requireSuccess(effective, "Read effective hook configuration");
    }
    const [scope, path] = effective.stdout.split("\0");
    if (scope === "global" && [".husky", ".husky/", ".husky/_", ".husky/_/"].includes(path)) {
      // A local override preserves the user's global configuration and works
      // for linked worktrees, whose common Git directory is outside the tree.
      const common = git(["rev-parse", "--git-common-dir"]);
      requireSuccess(common, "Find shared Git hooks directory");
      requireSuccess(localConfig(["--replace-all", "core.hooksPath", resolve(common.stdout.trim(), "hooks")]), "Select default Git hooks directory");
      changed = true;
    }

    const installed = spawnSync("lefthook", ["install"], {
      stdio: "inherit",
      // Windows package managers expose command shims; arguments are fixed.
      shell: process.platform === "win32",
    });
    if (installed.status === 0 && !installed.error) return 0;

    if (changed) {
      restoreLocal(previous);
      changed = false;
      console.error("Lefthook installation failed; the previous hook configuration was restored.");
    }
    if (installed.error) console.error(installed.error.message);
    return installed.status && installed.status > 0 ? installed.status : 1;
  } catch (error) {
    if (changed) restoreLocal(previous);
    throw error;
  }
}

try {
  process.exitCode = installHooks();
} catch (error) {
  console.error(`Hook installation failed: ${error.message}`);
  process.exitCode = 1;
}
