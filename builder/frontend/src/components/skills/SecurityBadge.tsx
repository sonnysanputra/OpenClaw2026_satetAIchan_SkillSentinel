"use client";
import { Badge } from "@/components/ui/badge";
import type { SecurityStatus } from "@/types";
import { Loader2 } from "lucide-react";

export function SecurityBadge({ status }: { status: SecurityStatus }) {
  switch (status) {
    case "pending":
      return <Badge variant="secondary">Pending review</Badge>;
    case "reviewing":
      return (
        <Badge variant="info" className="gap-1">
          <Loader2 className="h-3 w-3 animate-spin" /> Reviewing…
        </Badge>
      );
    case "approved":
      return <Badge variant="success">Approved</Badge>;
    case "blocked":
      return <Badge variant="destructive">Blocked</Badge>;
    case "overridden":
      return <Badge variant="warning">Overridden</Badge>;
  }
}
