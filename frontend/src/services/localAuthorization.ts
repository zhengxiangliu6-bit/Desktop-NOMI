// Local backend capability, NOT an LLM API key. Ephemeral page memory only.
// Kept across settings-panel close so authorized chat can continue; reload discards it.
let capability: string | null = null;
export const getLocalAuthorization = () => capability;
export const setLocalAuthorization = (value: string | null) => {
  capability = value;
};
