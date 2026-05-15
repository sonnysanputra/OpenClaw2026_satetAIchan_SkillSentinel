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
    <div className="card-sentinel p-3 transition-colors hover:border-border/80">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold">{skill.name}</div>
          <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
            {skill.description}
          </div>
        </div>
        <Button
          size="sm"
          variant={added ? "cream" : "default"}
          onClick={onAdd}
          disabled={added}
          className="shrink-0"
        >
          {added ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          {added ? "Added" : "Add"}
        </Button>
      </div>
      <div className="mt-2.5 flex items-center gap-2">
        <Badge variant="outline" className="text-[10px] px-2 py-0">
          {skill.category}
        </Badge>
        <span className="text-xs text-muted-foreground">{skill.author}</span>
        {skill.install_count > 0 && (
          <span className="text-xs text-muted-foreground">
            · {skill.install_count.toLocaleString()} installs
          </span>
        )}
      </div>
    </div>
  );
}
