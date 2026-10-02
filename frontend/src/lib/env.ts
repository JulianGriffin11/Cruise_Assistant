// Empty in production: the API is served from the same origin as the SPA.
const raw = import.meta.env.VITE_API_BASE_URL;
export const apiBaseUrl =
  typeof raw === "string" ? raw.trim().replace(/\/$/, "") : "";
