// Types mirror backend/schemas/models.py — keep in sync.

export type AuthMethod = "key" | "password";
export type GroupChatMode = "mention" | "all" | "silent";

export interface VpsConfig {
  host: string;
  user: string;
  port: number;
  auth_method: AuthMethod;
  ssh_private_key: string;
  ssh_password: string;
}

export interface IdentityConfig {
  agent_name: string;
  agent_id: string;
  emoji: string;
  theme: string;
  workspace_path: string;
}

export interface PersonaConfig {
  tone: string;
  traits: string[];
  avoid: string;
}

export interface UserContextConfig {
  user_name: string;
  user_role: string;
  user_location: string;
  user_prefs: string;
  user_extra: string;
}

export interface InstructionsConfig {
  responsibilities: string;
  memory_rules: string;
  group_chat: GroupChatMode;
  security_rules: boolean;
}

export interface ModelConfig {
  provider: string;
  model: string;
  heartbeat_model: string;
  api_key: string;
}

export interface ChannelsConfig {
  selected: string[];
  account_ids: Record<string, string>;
}

export type SecurityStatus =
  | "pending"
  | "reviewing"
  | "approved"
  | "blocked"
  | "overridden";

export interface SkillItem {
  id: string;
  name: string;
  description: string;
  author: string;
  category?: string;
  install_count?: number;
  raw_url: string;
  security_status: SecurityStatus;
  security_reason: string | null;
}

// ---- API DTOs ----
export interface SkillCatalogItem {
  id: string;
  name: string;
  description: string;
  author: string;
  category: string;
  install_count: number;
  raw_url: string;
}

export interface SkillsListResponse {
  skills: SkillCatalogItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface SshTestRequest {
  host: string;
  user: string;
  port: number;
  auth_method: AuthMethod;
  ssh_private_key?: string | null;
  ssh_password?: string | null;
}

export interface SshTestResponse {
  success: boolean;
  os?: string | null;
  openclaw_installed?: boolean | null;
  error?: string | null;
}

export interface SkillReviewRequest {
  skills: { id: string; name: string; raw_url: string }[];
}

export interface SkillReviewResult {
  id: string;
  status: "approved" | "blocked";
  reason: string | null;
}

export interface SkillReviewResponse {
  results: SkillReviewResult[];
}

export interface DeploySkillItem {
  id: string;
  name: string;
  raw_url: string;
  security_status: "approved" | "overridden";
  security_reason: string | null;
}

export interface DeployRequest {
  vps: VpsConfig;
  identity: IdentityConfig;
  persona: PersonaConfig;
  user_context: UserContextConfig;
  instructions: InstructionsConfig;
  model: ModelConfig;
  channels: ChannelsConfig;
  skills: DeploySkillItem[];
}

export interface FilePreviewResponse {
  soul_md: string;
  user_md: string;
  agents_md: string;
  identity_md: string;
}

// ---- WS frames ----
export interface LogMessage {
  type: "log";
  level: "info" | "success" | "warning" | "error";
  message: string;
}

export interface StatusMessage {
  type: "status";
  status: "deploying" | "completed" | "failed";
  error?: string | null;
}

export type WsMessage = LogMessage | StatusMessage;
