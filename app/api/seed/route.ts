import { exportState, seedDemo } from "@/lib/playbook";
import { NextResponse } from "next/server";

export async function POST() {
  await seedDemo();
  const state = await exportState();
  return NextResponse.json({ ok: true, state });
}
