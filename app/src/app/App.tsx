import { I18nProvider } from '@cloudscape-design/components/i18n';
import enMessages from '@cloudscape-design/components/i18n/messages/all.en';
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import axios from "axios";
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
  axios.defaults.baseURL = `${import.meta.env.VITE_APIGW}${import.meta.env.VITE_BASE}${import.meta.env.VITE_API_PATH}`;
  axios.defaults.timeout = 30000;
  axios.defaults.headers.common = {
    'Content-Type': 'application/json',
  };

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