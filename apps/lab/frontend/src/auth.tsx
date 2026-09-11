import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type AuthRole = "member" | "approver" | "admin";

export type AuthUser = {
  userId: number;
  username: string;
  displayName: string;
  role: AuthRole;
  passwordChangeRequired: boolean;
};

type AuthStatus = "loading" | "authenticated" | "guest";

type AuthContextValue = {
  user: AuthUser | null;
  status: AuthStatus;
  error: string;
  login: (username: string, password: string) => Promise<AuthUser>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
};

type AuthApiUser = {
  user_id: number;
  username: string;
  display_name: string;
  role: AuthRole;
  password_change_required: boolean;
};

type AuthApiResponse = {
  result: "success" | "error";
  data: AuthApiUser | null;
  message: string;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function buildAuthApiUrl(path: string): string {
  if (API_BASE_URL) {
    return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
  }
  if (window.location.port === "5173") {
    return `http://localhost:8000${path}`;
  }
  return path;
}

function toAuthUser(user: AuthApiUser): AuthUser {
  return {
    userId: user.user_id,
    username: user.username,
    displayName: user.display_name,
    role: user.role,
    passwordChangeRequired: user.password_change_required,
  };
}

async function readAuthResponse(response: Response): Promise<AuthApiResponse> {
  try {
    return (await response.json()) as AuthApiResponse;
  } catch {
    return {
      result: "error",
      data: null,
      message: `認証APIから不正な応答が返りました。HTTP ${response.status}`,
    };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    const abortController = new AbortController();

    async function restoreSession(): Promise<void> {
      try {
        const response = await fetch(buildAuthApiUrl("/api/v1/auth/me"), {
          credentials: "include",
          signal: abortController.signal,
        });
        const body = await readAuthResponse(response);
        if (response.ok && body.result === "success" && body.data !== null) {
          setUser(toAuthUser(body.data));
          setStatus("authenticated");
          setError("");
          return;
        }
        setUser(null);
        setStatus("guest");
        setError(response.status === 401 ? "" : body.message);
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") {
          return;
        }
        setUser(null);
        setStatus("guest");
        setError("認証APIへ接続できませんでした。");
      }
    }

    void restoreSession();
    return () => abortController.abort();
  }, []);

  async function login(username: string, password: string): Promise<AuthUser> {
    const response = await fetch(buildAuthApiUrl("/api/v1/auth/login"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const body = await readAuthResponse(response);
    if (!response.ok || body.result !== "success" || body.data === null) {
      setUser(null);
      setStatus("guest");
      throw new Error(body.message || "ログインに失敗しました。");
    }
    const authenticatedUser = toAuthUser(body.data);
    setUser(authenticatedUser);
    setStatus("authenticated");
    setError("");
    return authenticatedUser;
  }

  async function changePassword(currentPassword: string, newPassword: string): Promise<AuthUser> {
    const response = await fetch(buildAuthApiUrl("/api/v1/auth/change-password"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    const body = await readAuthResponse(response);
    if (!response.ok || body.result !== "success" || body.data === null) {
      throw new Error(body.message || "パスワードを変更できませんでした。");
    }
    const updatedUser = toAuthUser(body.data);
    setUser(updatedUser);
    setStatus("authenticated");
    setError("");
    return updatedUser;
  }

  async function logout(): Promise<void> {
    try {
      await fetch(buildAuthApiUrl("/api/v1/auth/logout"), {
        method: "POST",
        credentials: "include",
      });
    } finally {
      setUser(null);
      setStatus("guest");
      setError("");
    }
  }

  const value = useMemo(
    () => ({ user, status, error, login, changePassword, logout }),
    [user, status, error],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
