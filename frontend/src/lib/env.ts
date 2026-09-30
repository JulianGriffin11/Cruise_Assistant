const raw = import.meta.env.VITE_API_BASE_URL;
if (typeof raw !== "string" || raw.trim() === "") {
  throw new Error("VITE_API_BASE_URL is required");
}

export const apiBaseUrl = raw.replace(/\/$/, "");
