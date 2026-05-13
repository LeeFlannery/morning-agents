import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { BriefingOutput, RunManifestEntry } from "./schemas";

export function useRunManifest() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: async () => {
      const res = await fetch("/api/runs");
      if (!res.ok) throw new Error(`Failed to fetch runs: ${res.status}`);
      return z.array(RunManifestEntry).parse(await res.json());
    },
    refetchInterval: 30_000,
  });
}

export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: async () => {
      const res = await fetch(`/api/runs/${runId}.json`);
      if (!res.ok) throw new Error(`Run not found: ${runId}`);
      return BriefingOutput.parse(await res.json());
    },
    enabled: !!runId,
    staleTime: Infinity,
  });
}
