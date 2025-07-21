import { createBrowserRouter } from 'react-router-dom';
import App from "./App.tsx";
import ErrorPage from './pages/ErrorPage';

import ListMessages from '../feature/email/components/list/ListMessages.tsx';
import ListFolders from '../feature/folders/components/list/ListFolders.tsx';
import CreateFolder from '../feature/folders/components/create/CreateFolder.tsx';
import CreateRule from '../feature/rules/components/create/CreateRule.tsx';
import ListRules from '../feature/rules/components/list/ListRules.tsx';

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
      },
      {
        path: "folders",
        handle: "Folders",
        children: [
          {
            index: true,
            element: <ListFolders />,
          },
          {
            path: "create",
            element: <CreateFolder />,
            handle: "Create Folder"
          },
          {
            path: ":folder_id",
            element: <ListMessages />,
            handle: {
              crumb: (name: string) => name
            },
          }
        ]
      },
      {
        path: "rules",
        handle: "Rules",
        children: [
          {
            index: true,
            element: <ListRules />,
          },
          {
            path: "create",
            handle: "Create Rule",
            element: <CreateRule />,
          }
        ]
      }
    ]
  }
]);
