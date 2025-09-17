import { createBrowserRouter } from 'react-router-dom';
import App from "./App.tsx";
import ErrorPage from './pages/ErrorPage';

import ListMessages from '../feature/email/components/list/ListMessages.tsx';

export const router = createBrowserRouter([
  {
    path: import.meta.env.VITE_BASE,
    element: <App />,
    errorElement: <ErrorPage />,
    handle: "Home",
    children: [
      {
        index: true,
        element: <ListMessages />
      },
      /* {
        path: "logout",
        element: <AuthPage />,
      }, */
      {
        path: "messages",
        handle: "Messages",
        children: [
          {
            index: true,
            element: <ListMessages />
          },
        ]
      }
    ]
  }
]);
