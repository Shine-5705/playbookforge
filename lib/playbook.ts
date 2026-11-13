import { execFile } from "child_process";
import { promisify } from "util";
import fs from "fs/promises";
import path from "path";

const execFileAsync = promisify(execFile);

export const REPO_ROOT = path.join(process.cwd());

export type PlaybookRule = {
  id: string;
  version: number;
  text: string;
  status: string;
  pass_rate_before: number | null;
  pass_rate_after: number | null;
  simulated: boolean;
  created_at: string;
  parent_version: number | null;
};

export type DashboardState = {
  rules: PlaybookRule[];
  latest_replay: Record<string, unknown> | null;
  demo_mode: string;
};

export async function runPf(args: string[]): Promise<string> {
  const env = {
    ...process.env,
    PYTHONPATH: path.join(REPO_ROOT, "backend"),
    DEMO_MODE: process.env.DEMO_MODE ?? "true",
  };
  const { stdout } = await execFileAsync("python3", ["-m", "playbookforge.cli", ...args], {
    cwd: REPO_ROOT,
    env,
    maxBuffer: 10 * 1024 * 1024,
  });
  return stdout.trim();
}

export async function loadDashboardState(): Promise<DashboardState> {
  const exportPath = path.join(REPO_ROOT, "data", "dashboard_export.json");
  try {
    const raw = await fs.readFile(exportPath, "utf-8");
    return JSON.parse(raw) as DashboardState;
  } catch {
    await seedDemo();
    const raw = await fs.readFile(exportPath, "utf-8");
    return JSON.parse(raw) as DashboardState;
  }
}

export async function seedDemo(): Promise<void> {
  await runPf(["seed"]);
  await runPf(["export", "--out", "data/dashboard_export.json"]);
}

export async function exportState(): Promise<DashboardState> {
  const out = await runPf(["export", "--out", "data/dashboard_export.json"]);
  const raw = await fs.readFile(out, "utf-8");
  return JSON.parse(raw) as DashboardState;
}
