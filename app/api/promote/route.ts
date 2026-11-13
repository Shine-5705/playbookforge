import { exportState, runPf } from "@/lib/playbook";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = (await req.json()) as { ruleId: string; version: number };
  try {
    await runPf(["promote", body.ruleId, "--version", String(body.version)]);
    const state = await exportState();
    return NextResponse.json({ ok: true, state });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Promotion failed";
    return NextResponse.json({ ok: false, error: message }, { status: 400 });
  }
}
