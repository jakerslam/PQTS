export type OperatorActionKind =
  | "pause_trading"
  | "resume_trading"
  | "canary_promote"
  | "canary_hold"
  | "ack_incident";

export interface OperatorActionRecord {
  id: string;
  kind: OperatorActionKind;
  actor: string;
  note: string;
  createdAt: string;
}

const actionLog: OperatorActionRecord[] = [];

function actionId(): string {
  return `op_${Math.random().toString(36).slice(2, 10)}`;
}

export function recordOperatorAction(
  payload: Omit<OperatorActionRecord, "id" | "createdAt">,
): OperatorActionRecord {
  const entry: OperatorActionRecord = {
    id: actionId(),
    kind: payload.kind,
    actor: payload.actor,
    note: payload.note,
    createdAt: new Date().toISOString(),
  };
  actionLog.unshift(entry);
  if (actionLog.length > 250) {
    actionLog.length = 250;
  }
  return entry;
}

export function listOperatorActions(limit = 50): OperatorActionRecord[] {
  return actionLog.slice(0, Math.max(limit, 1));
}
