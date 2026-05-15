"use client";
import type { SkillCatalogItem } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Check } from "lucide-react";

export function SkillCard({
  skill,
  added,
  onAdd,
}: {
  skill: SkillCatalogItem;
  added: boolean;
  onAdd: () => void;
}) {
  return (
    <div className="rounded-md border p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-medium">{skill.name}</div>
          <div className="line-clamp-2 text-xs text-muted-foreground">{skill.description}</div>
        </div>
        <Button size="sm" variant={added ? "secondary" : "default"} onClick={onAdd} disabled={added}>
          {added ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          {added ? "Added" : "Add"}
        </Button>
      </div>
      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline">{skill.category}</Badge>
        <span>{skill.author}</span>
        {skill.install_count > 0 && <span>· {skill.install_count.toLocaleString()} installs</span>}
      </div>
    </div>
  );
}
