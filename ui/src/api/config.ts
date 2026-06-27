/** SuperNEXUS API base URL — single source of truth */
export const API = typeof window !== "undefined" && window.location.port === "3000"
  ? ""
  : typeof window !== "undefined" && window.location.port === "9000"
    ? `${window.location.protocol}//${window.location.host}`
    : "http://localhost:9000";
