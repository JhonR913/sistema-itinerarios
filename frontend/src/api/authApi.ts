import { apiRequest } from "../lib/httpClient";

interface IssueTokenResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
}

export const authApi = {
  issueToken: (username: string) =>
    apiRequest<IssueTokenResponse>("/api/auth/token", { method: "POST", body: { username } }),
};
