import {
  Dispatch,
  SetStateAction,
} from "react";
import {
  AppLayoutProps,
  FlashbarProps
} from "@cloudscape-design/components";
import { QueryObserverResult } from "@tanstack/react-query";
import { Folder } from "../../folders/types";

export type AppHelperContextType = {
  setNotifications: Dispatch<SetStateAction<FlashbarProps.MessageDefinition[]>>;
  setCurrentBreadcrumbDetailPageName: Dispatch<SetStateAction<string>>;
  setActiveDrawerId: Dispatch<SetStateAction<string>>;
  setActiveDrawer: Dispatch<SetStateAction<AppLayoutProps.Drawer[]>>;
  refetchFolders: () => Promise<QueryObserverResult<Folder[], Error>>;
};