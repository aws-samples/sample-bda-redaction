// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { AuthProvider } from "react-oidc-context";
import { User, WebStorageStateStore } from "oidc-client-ts";
import { router } from './Router';
// import { OidcClientSettings } from 'oidc-client-ts';

const oidcConfig = {
  authority: import.meta.env.VITE_OIDC_DOMAIN,
  client_id: import.meta.env.VITE_OIDC_CLIENT_ID,
  scope: import.meta.env.VITE_OIDC_SCOPES,
  redirect_uri: window.location.origin,
  post_logout_redirect_uri: window.location.origin,
  automaticSilentRenew: true,
  ...(import.meta.env.VITE_OIDC_METADATA_URL !== "" && {
    metadataUrl: import.meta.env.VITE_OIDC_METADATA_URL
  }),
  ...(import.meta.env.VITE_OIDC_ISSUER !== "" && {
    metadata: {
      issuer: import.meta.env.VITE_OIDC_METADATA_ISSUER,
      authorization_endpoint: import.meta.env.VITE_OIDC_METADATA_AUTHORIZATION_ENDPOINT,
      token_endpoint: import.meta.env.VITE_OIDC_METADATA_TOKEN_ENDPOINT,
      userinfo_endpoint: import.meta.env.VITE_OIDC_METADATA_USERINFO_ENDPOINT,
      jwks_uri: import.meta.env.VITE_OIDC_METADATA_JWKS_URI,
      introspection_endpoint: import.meta.env.VITE_OIDC_METADATA_INTROSPECTION_ENDPOINT,
      revocation_endpoint: import.meta.env.VITE_OIDC_METADATA_REVOCATION_ENDPOINT,
      end_session_endpoint: import.meta.env.VITE_OIDC_METADATA_END_SESSION_ENDPOINT,
      response_types_supported: import.meta.env.VITE_OIDC_METADATA_RESPONSE_TYPES_SUPPORTED.split(","),
      subject_types_supported: import.meta.env.VITE_OIDC_METADATA_SUBJECT_TYPES_SUPPORTED.split(","),
    }
  }),
  extraQueryParams: {
    audience: import.meta.env.VITE_OIDC_AUDIENCE
  },
  userStore: new WebStorageStateStore({ store: window.localStorage }),
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onSigninCallback: (_user: User|void): void => {
    window.history.replaceState(
      {},
      document.title,
      window.location.pathname
    )
  },
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider {...oidcConfig}>
      <RouterProvider router={router} />
    </AuthProvider>
  </React.StrictMode>,
)