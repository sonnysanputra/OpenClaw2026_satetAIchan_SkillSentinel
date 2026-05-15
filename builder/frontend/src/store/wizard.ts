"use client";
import { create } from "zustand";
import type {
  ChannelsConfig,
  IdentityConfig,
  InstructionsConfig,
  ModelConfig,
  PersonaConfig,
  SkillItem,
  UserContextConfig,
  VpsConfig,
} from "@/types";

interface WizardState {
  currentStep: number;
  vps: VpsConfig;
  identity: IdentityConfig;
  persona: PersonaConfig;
  user_context: UserContextConfig;
  instructions: InstructionsConfig;
  model: ModelConfig;
  channels: ChannelsConfig;
  skills: SkillItem[];
  // workspace_path was manually edited?
  workspaceManuallyEdited: boolean;

  setStep: (n: number) => void;
  updateVps: (p: Partial<VpsConfig>) => void;
  updateIdentity: (p: Partial<IdentityConfig>) => void;
  updatePersona: (p: Partial<PersonaConfig>) => void;
  updateUserContext: (p: Partial<UserContextConfig>) => void;
  updateInstructions: (p: Partial<InstructionsConfig>) => void;
  updateModel: (p: Partial<ModelConfig>) => void;
  updateChannels: (p: Partial<ChannelsConfig>) => void;
  setSkills: (s: SkillItem[]) => void;
  addSkill: (s: SkillItem) => void;
  removeSkill: (id: string) => void;
  patchSkill: (id: string, patch: Partial<SkillItem>) => void;
  setWorkspaceManuallyEdited: (b: boolean) => void;

  reset: () => void;
}

const defaults: Omit<
  WizardState,
  | "setStep"
  | "updateVps"
  | "updateIdentity"
  | "updatePersona"
  | "updateUserContext"
  | "updateInstructions"
  | "updateModel"
  | "updateChannels"
  | "setSkills"
  | "addSkill"
  | "removeSkill"
  | "patchSkill"
  | "setWorkspaceManuallyEdited"
  | "reset"
> = {
  currentStep: 0,
  vps: {
    host: "",
    user: "root",
    port: 22,
    auth_method: "key",
    ssh_private_key: "",
    ssh_password: "",
  },
  identity: {
    agent_name: "",
    agent_id: "",
    emoji: "🦞",
    theme: "",
    workspace_path: "",
  },
  persona: { tone: "friendly", traits: [], avoid: "" },
  user_context: {
    user_name: "",
    user_role: "",
    user_location: "",
    user_prefs: "",
    user_extra: "",
  },
  instructions: {
    responsibilities: "",
    memory_rules: "",
    group_chat: "mention",
    security_rules: true,
  },
  model: {
    provider: "anthropic",
    model: "claude-sonnet-4-20250514",
    heartbeat_model: "",
    api_key: "",
  },
  channels: { selected: [], account_ids: {} },
  skills: [],
  workspaceManuallyEdited: false,
};

export const useWizard = create<WizardState>((set) => ({
  ...defaults,
  setStep: (n) => set({ currentStep: n }),
  updateVps: (p) => set((s) => ({ vps: { ...s.vps, ...p } })),
  updateIdentity: (p) => set((s) => ({ identity: { ...s.identity, ...p } })),
  updatePersona: (p) => set((s) => ({ persona: { ...s.persona, ...p } })),
  updateUserContext: (p) =>
    set((s) => ({ user_context: { ...s.user_context, ...p } })),
  updateInstructions: (p) =>
    set((s) => ({ instructions: { ...s.instructions, ...p } })),
  updateModel: (p) => set((s) => ({ model: { ...s.model, ...p } })),
  updateChannels: (p) => set((s) => ({ channels: { ...s.channels, ...p } })),
  setSkills: (skills) => set({ skills }),
  addSkill: (s) =>
    set((state) =>
      state.skills.some((x) => x.id === s.id)
        ? state
        : { skills: [...state.skills, s] },
    ),
  removeSkill: (id) =>
    set((state) => ({ skills: state.skills.filter((x) => x.id !== id) })),
  patchSkill: (id, patch) =>
    set((state) => ({
      skills: state.skills.map((x) => (x.id === id ? { ...x, ...patch } : x)),
    })),
  setWorkspaceManuallyEdited: (b) => set({ workspaceManuallyEdited: b }),
  reset: () => set({ ...defaults }),
}));
