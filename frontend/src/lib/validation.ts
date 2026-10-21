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

// Contract pattern for repositoryUrl (_docs/openapi.yaml, NewAssetInput).
const REPOSITORY_URL = /^https:\/\/github\.com\/[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\/(?!\.{1,2}$)(?!.*\.git$)[A-Za-z0-9_.-]{1,100}$/;

export function validateRepositoryUrl(url: string): string | null {
  if (!REPOSITORY_URL.test(url.trim())) {
    return "Repository URL must look like https://github.com/<owner>/<repo>.";
  }
  return null;
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Blank is allowed (stored as null); a non-blank value must be an email address. */
export function validateOwnerEmail(email: string | null): string | null {
  const trimmed = email?.trim() ?? "";
  if (trimmed === "") return null;
  return EMAIL.test(trimmed) ? null : "Owner email must be an email address.";
}
