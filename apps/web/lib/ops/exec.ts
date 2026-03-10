import { execFile } from "node:child_process";

import { resolveRepoRoot } from "@/lib/ops/repo-root";

export interface ExecResult {
  ok: boolean;
  command: string[];
  exit_code: number;
  stdout: string;
  stderr: string;
}

export async function runPython(
  args: string[],
  opts?: {
    timeoutMs?: number;
  },
): Promise<ExecResult> {
  const command = ["python3", ...args];
  const cwd = resolveRepoRoot();
  const timeoutMs = opts?.timeoutMs ?? 120_000;
  return new Promise<ExecResult>((resolve) => {
    execFile(
      command[0],
      command.slice(1),
      { cwd, timeout: timeoutMs, maxBuffer: 8 * 1024 * 1024 },
      (error, stdout, stderr) => {
        const code = typeof (error as any)?.code === "number" ? Number((error as any).code) : 0;
        resolve({
          ok: code === 0,
          command,
          exit_code: code,
          stdout: String(stdout ?? ""),
          stderr: String(stderr ?? ""),
        });
      },
    );
  });
}
