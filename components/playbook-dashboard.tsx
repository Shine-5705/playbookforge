"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import type { DashboardState, PlaybookRule } from "@/lib/playbook";

const chartConfig = {
  before: { label: "Before rule", color: "hsl(var(--chart-2))" },
  after: { label: "After rule", color: "hsl(var(--chart-1))" },
} satisfies ChartConfig;

function statusVariant(status: string): "default" | "secondary" | "outline" | "destructive" {
  if (status === "promoted") return "default";
  if (status === "rolled_back") return "destructive";
  return "secondary";
}

export function PlaybookDashboard() {
  const [state, setState] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const res = await fetch("/api/state");
    setState(await res.json());
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const latestByRule = useMemo(() => {
    if (!state) return [] as PlaybookRule[];
    const map = new Map<string, PlaybookRule>();
    for (const r of state.rules) {
      const prev = map.get(r.id);
      if (!prev || r.version > prev.version) map.set(r.id, r);
    }
    return [...map.values()].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
  }, [state]);

  const chartData = useMemo(() => {
    return latestByRule
      .filter((r) => r.pass_rate_before != null && r.pass_rate_after != null)
      .map((r) => ({
        rule: r.text.slice(0, 28) + (r.text.length > 28 ? "…" : ""),
        before: Math.round((r.pass_rate_before ?? 0) * 100),
        after: Math.round((r.pass_rate_after ?? 0) * 100),
      }));
  }, [latestByRule]);

  const replay = state?.latest_replay as {
    simulated?: boolean;
    baseline?: { task_id: string; passed: boolean; diff_summary: string }[];
    with_rule?: { task_id: string; passed: boolean; diff_summary: string }[];
    per_task_improved?: Record<string, boolean>;
    per_task_regressed?: Record<string, boolean>;
  } | null;

  const simulated = state?.demo_mode !== "false" && latestByRule.some((r) => r.simulated);

  async function action(path: string, body: object, label: string) {
    setBusy(label);
    try {
      const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error ?? "Request failed");
      setState(data.state ?? (await (await fetch("/api/state")).json()));
      toast.success(label);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center text-muted-foreground">
        Loading PlaybookForge demo…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900">
      <header className="border-b bg-white/80 dark:bg-slate-950/80 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto max-w-6xl px-4 py-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">PlaybookForge</h1>
            <p className="text-sm text-muted-foreground">
              Distil failed agent runs into versioned, test-gated playbook rules
            </p>
          </div>
          <div className="flex items-center gap-2">
            {simulated && (
              <Badge variant="outline" className="border-amber-500 text-amber-700 dark:text-amber-300">
                Simulated agent benchmarks
              </Badge>
            )}
            <Button
              variant="outline"
              size="sm"
              disabled={!!busy}
              onClick={() => action("/api/seed", {}, "Demo re-seeded")}
            >
              Re-seed demo
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 space-y-8">
        <section className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Rules in timeline</CardDescription>
              <CardTitle className="text-3xl">{latestByRule.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Promoted</CardDescription>
              <CardTitle className="text-3xl">
                {latestByRule.filter((r) => r.status === "promoted").length}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Mode</CardDescription>
              <CardTitle className="text-lg">
                {simulated ? "DEMO_MODE (simulated replay)" : "Live replay"}
              </CardTitle>
            </CardHeader>
          </Card>
        </section>

        <section className="grid gap-6 lg:grid-cols-5">
          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle>Pass rate before / after rule injection</CardTitle>
              <CardDescription>
                {simulated
                  ? "Values from the labelled simulated agent — not real LLM benchmarks."
                  : "Measured on the bundled task suite replay harness."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {chartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">Run replay on a candidate rule to populate chart.</p>
              ) : (
                <ChartContainer config={chartConfig} className="h-72 w-full">
                  <BarChart data={chartData} margin={{ left: 8, right: 8 }}>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="rule" tickLine={false} axisLine={false} fontSize={11} />
                    <YAxis unit="%" domain={[0, 100]} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar dataKey="before" fill="var(--color-before)" radius={4} />
                    <Bar dataKey="after" fill="var(--color-after)" radius={4} />
                  </BarChart>
                </ChartContainer>
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Rule timeline</CardTitle>
              <CardDescription>Versioned in SQLite with one-click rollback</CardDescription>
            </CardHeader>
            <CardContent className="max-h-72 overflow-y-auto space-y-3 pr-1">
              {state?.rules.slice().reverse().map((r) => (
                <div key={`${r.id}-${r.version}`} className="rounded-lg border p-3 text-sm">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <Badge variant={statusVariant(r.status)}>{r.status}</Badge>
                    <span className="text-xs text-muted-foreground">v{r.version}</span>
                  </div>
                  <p className="leading-snug">{r.text}</p>
                  {r.pass_rate_before != null && r.pass_rate_after != null && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Pass rate {Math.round(r.pass_rate_before * 100)}% → {Math.round(r.pass_rate_after * 100)}%
                      {r.simulated ? " (simulated)" : ""}
                    </p>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </section>

        <Card>
          <CardHeader>
            <CardTitle>Candidate rules</CardTitle>
            <CardDescription>Promote only when pass rate rises with zero per-task regressions</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Pass rate</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {latestByRule.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="max-w-md whitespace-normal">{r.text}</TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(r.status)}>{r.status}</Badge>
                    </TableCell>
                    <TableCell>
                      {r.pass_rate_before == null
                        ? "—"
                        : `${Math.round(r.pass_rate_before * 100)}% → ${Math.round((r.pass_rate_after ?? 0) * 100)}%`}
                    </TableCell>
                    <TableCell className="text-right space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!!busy}
                        onClick={() => action("/api/replay", { ruleId: r.id, version: r.version }, "Replay complete")}
                      >
                        Replay
                      </Button>
                      <Button
                        size="sm"
                        disabled={!!busy || r.status === "promoted"}
                        onClick={() => action("/api/promote", { ruleId: r.id, version: r.version }, "Rule promoted")}
                      >
                        Promote
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={!!busy}
                        onClick={() => action("/api/rollback", { ruleId: r.id }, "Rolled back")}
                      >
                        Rollback
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Per-task diff (latest replay)</CardTitle>
            <CardDescription>Baseline vs rule-injected agent outcome per bundled task</CardDescription>
          </CardHeader>
          <CardContent>
            {!replay?.baseline?.length ? (
              <p className="text-sm text-muted-foreground">No replay snapshot yet.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Task</TableHead>
                    <TableHead>Before</TableHead>
                    <TableHead>After</TableHead>
                    <TableHead>Δ</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {replay.baseline.map((b, i) => {
                    const a = replay.with_rule?.[i];
                    const improved = replay.per_task_improved?.[b.task_id];
                    const regressed = replay.per_task_regressed?.[b.task_id];
                    return (
                      <TableRow key={b.task_id}>
                        <TableCell className="font-mono text-xs">{b.task_id}</TableCell>
                        <TableCell>{b.passed ? "pass" : "fail"}</TableCell>
                        <TableCell>{a?.passed ? "pass" : "fail"}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {improved && "↑ improved"}
                          {regressed && "↓ regressed"}
                          {!improved && !regressed && "—"}
                          <div>{a?.diff_summary ?? b.diff_summary}</div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <p className="text-xs text-muted-foreground pb-8">
          Author: Shine Gupta (GitHub Shine-5705) · Adaply · HackerSquad AI Remote Hackathon · MIT License
        </p>
      </main>
    </div>
  );
}
