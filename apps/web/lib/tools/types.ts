export type ToolLifecycleStatus = "loading" | "complete" | "error";

export interface ToolLifecycleEvent<TPayload = unknown> {
  toolType: string;
  status: ToolLifecycleStatus;
  payload?: TPayload;
  startedAt?: string;
  endedAt?: string;
  errorMessage?: string;
}

export interface ToolRendererProps {
  event: ToolLifecycleEvent;
}

export interface ToolRendererRegistration {
  toolType: string;
  LoadingComponent: React.ComponentType<ToolRendererProps>;
  FinalComponent: React.ComponentType<ToolRendererProps>;
}
