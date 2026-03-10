import fs from "node:fs";
import path from "node:path";

function hasRepoMarkers(candidate: string): boolean {
  return (
    fs.existsSync(path.join(candidate, "README.md")) &&
    fs.existsSync(path.join(candidate, "results")) &&
    fs.existsSync(path.join(candidate, "main.py"))
  );
}

export function resolveRepoRoot(): string {
  const envRoot = process.env.PQTS_REPO_ROOT?.trim();
  if (envRoot && hasRepoMarkers(envRoot)) {
    return envRoot;
  }

  const cwd = process.cwd();
  if (hasRepoMarkers(cwd)) {
    return cwd;
  }

  const upOne = path.resolve(cwd, "..");
  if (hasRepoMarkers(upOne)) {
    return upOne;
  }

  const upTwo = path.resolve(cwd, "..", "..");
  if (hasRepoMarkers(upTwo)) {
    return upTwo;
  }

  return cwd;
}
