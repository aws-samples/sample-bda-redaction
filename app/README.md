## Install Prerequisites

This application requires the installation of the following software tools:
* [TypeScript](https://www.typescriptlang.org/)
* [Node v18 or higher](https://nodejs.org/en/download/package-manager)
* [NPM v9.8 or higher](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)
* [Yarn 1.22 or higher](https://yarnpkg.com/getting-started/install)

## Authentication

The portal is protected by Basic Authentication or authentication using OIDC. When using Basic Authentication the credentials are stored in Secrets Manager using the secret provisioned in the PortalStack that was created via CDK.

## Environment Variables

Update the following variables in the ```.env``` file (by copying the ```.env.example``` file to ```.env```)

| Environment Variable Name | Default | Description | Required |
| ------ | ---- | -------- | --------- |
| VITE_APIGW | | URL of API Gateway (without the path part) | Yes

Authentication through OpenID Connect (OIDC) requires the following environment variables to be set. Otherwise, they are optional if using Basic Access Authentication.

| Environment Variable Name | Default | Description |
| ------ | ---- | -------- |
| VITE_OIDC_DOMAIN |  | FQDN for the OIDC OP |
| VITE_OIDC_CLIENT_ID |  | Unique identifier for the OIDC RP |
| VITE_OIDC_AUDIENCE |  | The unique identifier (FQDN) of the API |
| VITE_OIDC_SCOPES | "openid email profile user_alias username" | The OIDC scopes that provide access to standard claims |
| VITE_OIDC_METADATA_URL | | OIDC Metadata URL |
| VITE_OIDC_LOGOUT_URL | | OIDC Logout URL (if not available through OIDC Metadata URL) |

If OIDC authentication is being used and your OIDC OP does not provide all of the necessary OIDC parameters through the metadata URL (VITE_OIDC_METADATA_URL) automatically, then you will need to provide the values for the following environment variables:

| Environment Variable | OIDC Parameter | Description | Default |
|---------------------|----------------|-------------|---------|
| VITE_OIDC_METADATA_ISSUER | issuer | URL that the OpenID Provider asserts as its Issuer Identifier | None |
| VITE_OIDC_METADATA_AUTHORIZATION_ENDPOINT | authorization_endpoint | URL of the OP's OAuth 2.0 Authorization Endpoint where authentication and authorization occurs | None |
| VITE_OIDC_METADATA_TOKEN_ENDPOINT | token_endpoint | URL of the OP's OAuth 2.0 Token Endpoint where access tokens are obtained | None |
| VITE_OIDC_METADATA_USERINFO_ENDPOINT | userinfo_endpoint | URL of the OP's UserInfo Endpoint where claims about the authenticated end-user can be obtained | None |
| VITE_OIDC_METADATA_JWKS_URI | jwks_uri | URL of the OP's JSON Web Key Set document containing signing keys | None |
| VITE_OIDC_METADATA_INTROSPECTION_ENDPOINT | introspection_endpoint | URL of the OP's OAuth 2.0 Token Introspection Endpoint for validating tokens | None |
| VITE_OIDC_METADATA_REVOCATION_ENDPOINT | revocation_endpoint | URL of the OP's OAuth 2.0 Token Revocation Endpoint for revoking tokens | None |
| VITE_OIDC_METADATA_END_SESSION_ENDPOINT | end_session_endpoint | URL of the OP's End Session Endpoint for logging out | None |
| VITE_OIDC_METADATA_RESPONSE_TYPES_SUPPORTED | response_types_supported | List of OAuth 2.0 response_type values supported by the OP | token,id_token,token id_token,code,code id_token,code token id_token,code token,none |
| VITE_OIDC_METADATA_SUBJECT_TYPES_SUPPORTED | subject_types_supported | List of Subject Identifier types supported by the OP | public |

## Local Development

Run the local development server by running the following commands:

- Install NPM packages
```sh
yarn install
```

- Create an environment file
```sh
cp .env.example .env
```

- Start the local development server

```sh
yarn dev
```

The local development server is managed by [Vite](https://vite.dev/) and will begin running locally on port **5173** by default. If you need [to customize the port, you can follow these directions](https://vite.dev/guide/cli).

### Preview Production Build

The production build of the application can also be viewed locally by running
```sh
yarn preview
```

By default, the preview of the production build will run locally on port **4173**. If you need [to customize the port, you can follow these instructions](https://vite.dev/guide/cli#vite-preview).

## Production Deployment

Perform the following steps to build this application for production

- Install NPM packages
```sh
yarn install
```

- Create an environment file
```sh
cp .env.example .env
```

- Add the URL of API Gateway to the .env file
```sh
VITE_APIGW=""
```

- Build the files
```sh
yarn build
```

After the build succeeds, transfer all of the files within the _dist/_ directory into the Amazon S3 bucket that is designated for these assets (specified in the PortalStack provisioned via CDK).

Example:
```sh
aws s3 sync dist/ s3://[name-of-bucket] --delete
```

Once the files have been transferred successfully, you can view the portal using either the API Gateway URL or the domain name that is configured to serve requests.