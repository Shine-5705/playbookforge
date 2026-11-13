import { exportState, runPf } from "@/lib/playbook";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = (await req.json()) as { ruleId: string };
  await runPf(["rollback", body.ruleId]);
  const state = await exportState();
  return NextResponse.json({ ok: true, state });
}
