"use client";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { listSkills } from "@/lib/api";
import { useWizard } from "@/store/wizard";
import type { SkillCatalogItem, SkillItem } from "@/types";
import { SkillCard } from "./SkillCard";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SkillBrowser() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const selected = useWizard((s) => s.skills);
  const addSkill = useWizard((s) => s.addSkill);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      setSearch(searchInput);
      setPage(1);
    }
  }

  const q = useQuery({
    queryKey: ["skills", search, page],
    queryFn: () => listSkills(search, page, 12),
  });

  const selectedIds = useMemo(() => new Set(selected.map((s) => s.id)), [selected]);

  function add(s: SkillCatalogItem) {
    const next: SkillItem = {
      id: s.id,
      name: s.name,
      description: s.description,
      author: s.author,
      category: s.category,
      install_count: s.install_count,
      raw_url: s.raw_url,
      content: s.content ?? null,
      security_status: "pending",
      security_reason: null,
    };
    addSkill(next);
  }

  return (
    <div className="rounded-lg border p-3">
      <Input
        placeholder="Search skills… (press Enter)"
        value={searchInput}
        onChange={(e) => setSearchInput(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <div className="mt-3 space-y-2 max-h-[500px] overflow-y-auto pr-1">
        {q.isLoading && (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
          </div>
        )}
        {q.error && <div className="text-sm text-destructive">{(q.error as Error).message}</div>}
        {q.data?.skills.map((sk) => (
          <SkillCard key={sk.id} skill={sk} added={selectedIds.has(sk.id)} onAdd={() => add(sk)} />
        ))}
        {q.data && q.data.skills.length === 0 && (
          <div className="py-8 text-center text-sm text-muted-foreground">No skills match.</div>
        )}
      </div>
      {q.data && q.data.total > 12 && (
        <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
          <span>Page {page} · {q.data.total} total</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>‹ Prev</Button>
            <Button size="sm" variant="outline" disabled={page * 12 >= q.data.total} onClick={() => setPage((p) => p + 1)}>Next ›</Button>
          </div>
        </div>
      )}
    </div>
  );
}
