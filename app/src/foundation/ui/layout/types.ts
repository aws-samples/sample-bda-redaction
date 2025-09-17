import {
  Dispatch,
  SetStateAction,
} from "react";
import {
  AppLayoutProps,
  FlashbarProps
} from "@cloudscape-design/components";

export type AppHelperContextType = {
  setNotifications: Dispatch<SetStateAction<FlashbarProps.MessageDefinition[]>>;
  setCurrentBreadcrumbDetailPageName: Dispatch<SetStateAction<string>>;
  setActiveDrawerId: Dispatch<SetStateAction<string>>;
  setActiveDrawer: Dispatch<SetStateAction<AppLayoutProps.Drawer[]>>;
};