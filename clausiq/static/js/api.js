/* Thin fetch wrapper around the ClausIQ REST API. */
const API = (() => {
  const TOKEN_KEY = "clausiq_token";
  const USER_KEY = "clausiq_user";

  const getToken = () => localStorage.getItem(TOKEN_KEY) || "";
  const setSession = (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  };
  const clearSession = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };
  const getUser = () => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); }
    catch { return null; }
  };

  async function request(method, path, body, isForm = false) {
    const headers = {};
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    let payload = body;
    if (body !== undefined && !isForm) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
    const res = await fetch(path, { method, headers, body: payload });
    if (res.status === 401 && !path.includes("/auth/login")) {
      clearSession();
      location.hash = "#/login";
      window.dispatchEvent(new Event("clausiq-auth-expired"));
      throw new Error("Session expired");
    }
    let data = null;
    try { data = await res.json(); } catch { /* empty body */ }
    if (!res.ok) {
      const detail = data && (data.detail || data.error) ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : `Request failed (${res.status})`;
      throw new Error(detail);
    }
    return data;
  }

  return {
    getToken, setSession, clearSession, getUser,
    get: (p) => request("GET", p),
    post: (p, b) => request("POST", p, b),
    put: (p, b) => request("PUT", p, b),
    del: (p) => request("DELETE", p),
    form: (p, formData) => request("POST", p, formData, true),
    login: (email, password) => request("POST", "/api/auth/login", { email, password }),
    logout: () => request("POST", "/api/auth/logout").catch(() => {}),
  };
})();
