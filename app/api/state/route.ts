import { loadDashboardState } from "@/lib/playbook";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const state = await loadDashboardState();
  return NextResponse.json(state);
}
