/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_COGNITO_CLIENT_ID?: string;
  readonly VITE_AWS_REGION?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "@capacitor-community/apple-sign-in" {
  export interface SignInWithAppleResponse {
    response: {
      user: string | null;
      email: string | null;
      givenName: string | null;
      familyName: string | null;
      identityToken: string;
      authorizationCode: string;
    };
  }
  export const SignInWithApple: {
    authorize(options: {
      clientId: string;
      redirectURI: string;
      scopes?: string;
    }): Promise<SignInWithAppleResponse>;
  };
}
