"use client";
import { useState } from "react";
import { useWizard } from "@/store/wizard";
import { Button } from "@/components/ui/button";
import { StepIndicator } from "@/components/wizard/StepIndicator";
import { StepVps, validateVps } from "@/components/wizard/StepVps";
import { StepIdentity, validateIdentity } from "@/components/wizard/StepIdentity";
import { StepPersona, validatePersona } from "@/components/wizard/StepPersona";
import { StepUserContext, validateUserContext } from "@/components/wizard/StepUserContext";
import { StepInstructions, validateInstructions } from "@/components/wizard/StepInstructions";
import { StepModel, validateModel } from "@/components/wizard/StepModel";
import { StepChannels, validateChannels } from "@/components/wizard/StepChannels";
import { StepSkills, validateSkills } from "@/components/wizard/StepSkills";
import { StepReview } from "@/components/wizard/StepReview";
import { ArrowLeft, ArrowRight } from "lucide-react";

const STEPS = [
  { label: "VPS", el: <StepVps />, validate: validateVps },
  { label: "Identity", el: <StepIdentity />, validate: validateIdentity },
  { label: "Persona", el: <StepPersona />, validate: validatePersona },
  { label: "About You", el: <StepUserContext />, validate: validateUserContext },
  { label: "Instructions", el: <StepInstructions />, validate: validateInstructions },
  { label: "Model", el: <StepModel />, validate: validateModel },
  { label: "Channels", el: <StepChannels />, validate: validateChannels },
  { label: "Skills", el: <StepSkills />, validate: validateSkills },
  { label: "Review", el: <StepReview />, validate: () => true },
];

export default function WizardPage() {
  const current = useWizard((s) => s.currentStep);
  const setStep = useWizard((s) => s.setStep);
  const [maxReached, setMaxReached] = useState(0);
  const state = useWizard();

  const stepValid = STEPS[current].validate(state);
  const isLast = current === STEPS.length - 1;

  function next() {
    const n = Math.min(current + 1, STEPS.length - 1);
    setStep(n);
    setMaxReached((m) => Math.max(m, n));
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <p className="label-tag">Multi-agent skill safety</p>
        <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
          Configure your agent
        </h1>
      </div>

      <StepIndicator
        current={current}
        maxReached={Math.max(maxReached, current)}
        onJump={setStep}
      />

      <div className="card-sentinel p-6">
        {STEPS[current].el}
      </div>

      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          disabled={current === 0}
          onClick={() => setStep(current - 1)}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </Button>
        {!isLast && (
          <Button disabled={!stepValid} onClick={next} className="gap-2">
            Next <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
