import {
  Box,
  Button,
  SpaceBetween,
  StatusIndicator
} from '@cloudscape-design/components';
import { I18nProvider } from '@cloudscape-design/components/i18n';
import enMessages from '@cloudscape-design/components/i18n/messages/all.en';
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import axios from "axios";
import { useAuth } from "react-oidc-context";
import AppCustomLayout from '../foundation/ui/layout/components/AppCustomLayout.tsx';
import AppHeader from '../foundation/ui/layout/components/AppHeader.tsx';
import AppFooter from '../foundation/ui/layout/components/AppFooter.tsx';

import "@cloudscape-design/global-styles/index.css";
import "../foundation/ui/layout/styles/App.scss";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
    },
  },
});

function App() {
  const auth = useAuth() ?? null;

  axios.defaults.baseURL = `${import.meta.env.VITE_APIGW}${import.meta.env.VITE_BASE}${import.meta.env.VITE_API_PATH}`;
  axios.defaults.timeout = 30000;
  axios.defaults.headers.common = {
    'Content-Type': 'application/json',
    ...(auth && {
      'Authorization': `Bearer ${auth.user?.id_token}`
    })
  };

  if(auth) {
    switch(auth.activeNavigator) {
      case "signinSilent":
        return (
          <Box variant="p" padding={{horizontal: "l", vertical: "l"}}>
            <StatusIndicator type="loading">
              Signing you in...
            </StatusIndicator>
          </Box>
        )
      case "signoutRedirect":
        return (
          <Box variant="p" padding={{horizontal: "l", vertical: "l"}}>
            <StatusIndicator type="loading">
              Signing you out...
            </StatusIndicator>
          </Box>
        );
    }

    if(auth.isLoading) {
      return (
        <Box variant="p" padding={{horizontal: "l", vertical: "l"}}>
          <StatusIndicator type="loading">
            Loading
          </StatusIndicator>
        </Box>
      );
    }

    if(auth.error) {
      return <div>Oops... {auth.error.message}</div>;
    }

    if(auth.isAuthenticated) {
      return (
        <I18nProvider locale='en' messages={[enMessages]}>
          <QueryClientProvider client={queryClient}>
            <AppHeader/>
            <AppCustomLayout />
            <AppFooter />
          </QueryClientProvider>
        </I18nProvider>
      );
    }

    return (
      <Box textAlign="center" padding={{horizontal: "xxxl", vertical: "xxxl"}}>
        <SpaceBetween size="l" direction="vertical">
          <Box variant="h1">
            PII Redaction using Amazon Bedrock
          </Box>
          <Button onClick={() => auth.signinRedirect({
            redirectMethod: 'replace',
          })} variant="primary">Login</Button>
        </SpaceBetween>
      </Box>
    );
  }

  return (
    <I18nProvider locale='en' messages={[enMessages]}>
      <QueryClientProvider client={queryClient}>
        <AppHeader/>
        <AppCustomLayout />
        <AppFooter />
      </QueryClientProvider>
    </I18nProvider>
  );
}

export default App;