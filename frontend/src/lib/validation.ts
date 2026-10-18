export function validateRiskReason(reason: string): string | null {
  if (!reason || reason.trim().length === 0) {
    return "A reason is required to accept this risk.";
  }
  return null;
}

export function validateAssetName(name: string): string | null {
  if (!name || name.trim().length === 0) return "Asset name is required.";
  return null;
}
