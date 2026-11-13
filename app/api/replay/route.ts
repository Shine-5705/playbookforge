import { exportState, runPf } from "@/lib/playbook";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = (await req.json()) as { ruleId: string; version?: number };
  const args = ["replay", body.ruleId];
  if (body.version != null) args.push("--version", String(body.version));
  await runPf(args);
  const state = await exportState();
  return NextResponse.json({ ok: true, state });
}
