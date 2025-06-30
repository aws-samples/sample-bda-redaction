// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { useState } from 'react';
import {
  AppLayout,
  AppLayoutProps,
  Badge,
  BreadcrumbGroup,
  Flashbar,
  FlashbarProps,
  SideNavigation,
} from '@cloudscape-design/components';
import { Outlet, useMatches, useNavigate } from 'react-router-dom';
import { useGetFolders } from '../../../../feature/folders/hooks/UseGetFolders';
import { Folder } from '../../../folders/types';
import { AppHelperContextType } from '../types';

type RouteMatchHandle = {
  crumb: (name: string) => string;
}

function AppCustomLayout() {
  const navigate = useNavigate();
  const routeMatches = useMatches();
  const { data: folders, refetch } = useGetFolders();
  const [activeHref, setActiveHref] = useState("/");
  const [navOpen, setNavOpen] = useState(true);

  const [notifications, setNotifications] = useState<FlashbarProps.MessageDefinition[]>([]);
  const [currentBreadcrumbDetailPageName, setCurrentBreadcrumbDetailPageName] = useState("");
  const [activeDrawerId, setActiveDrawerId] = useState("");
  const [activeDrawer, setActiveDrawer] = useState<AppLayoutProps.Drawer[]>([]);

  const breadcrumbItems = routeMatches
    .filter((route) => route.handle !== undefined)
    .map((route) => {
      const item = {
        href: route.pathname,
        disabled: true,
        text: ""
      };

      if(typeof route.handle === "string") {
        item.text = route.handle;
      } else {
        const handler = route.handle as RouteMatchHandle;
        item.text = handler.crumb(currentBreadcrumbDetailPageName);
      }

      return item;
    });

  function resetPanels() {
    setNotifications([]);
    // setActiveDrawerId("");
    // setActiveDrawer([]);
  }

  return (
    <AppLayout
      contentType="cards"
      activeDrawerId={activeDrawerId}
      onDrawerChange={(e) => setActiveDrawerId(e.detail.activeDrawerId!) }
      // headerVariant="high-contrast"
      notifications={
        <Flashbar
          items={
            notifications?.map((notification) => {
              return {
                ...notification,
                dismissible: true,
                dismissLabel: "Dismiss message",
                onDismiss: () => setNotifications([]),
              };
            })}
        />
      }
      breadcrumbs={
        <BreadcrumbGroup
          onClick={(e) => {
            e.preventDefault();
            resetPanels();
            navigate(e.detail.href, { replace: true });
          }}
          items={breadcrumbItems}
        />
      }
      drawers={activeDrawer}
      onNavigationChange={ () => setNavOpen(!navOpen) }
      navigationOpen={ navOpen }
      navigation={
        <SideNavigation
          activeHref={ activeHref }
          onFollow={event => {
            if (!event.detail.external) {
              event.preventDefault();
              setActiveHref(event.detail.href);
              navigate(event.detail.href, { replace: true });
              resetPanels();
            }
          }}
          items={[
            {
              type: "section-group",
              title: "Menu",
              items: [
                {
                  type: "link",
                  text: "Home",
                  href: `${import.meta.env.VITE_BASE}`
                },
                {
                  type: "link",
                  text: "Folders",
                  href: `${import.meta.env.VITE_BASE}/folders`
                },
                {
                  type: "link",
                  text: "Rules",
                  href: `${import.meta.env.VITE_BASE}/rules`
                }
              ]
            },
            {type: "divider"},
            {
              type: "section",
              text: "Folders",
              defaultExpanded: folders && folders?.length > 0,
              items: folders?.sort((a, b) => a.Name.localeCompare(b.Name))
                .map((folder: Folder) => {
                  return {
                    type: "link",
                    text: folder.Name,
                    href: `${import.meta.env.VITE_BASE}/folders/${folder.ID}`,
                    info: (folder.MessagesCount > 0) ? <Badge color="blue">{ folder.MessagesCount }</Badge>: ""
                  }
                }) ?? [
                  {
                    type: "link",
                    text: "Loading Folders...",
                    href: import.meta.env.VITE_BASE
                  }
                ]
            }
          ]}
        />
      }
      content={
        <Outlet context={
          {
            setNotifications,
            setCurrentBreadcrumbDetailPageName,
            setActiveDrawerId,
            setActiveDrawer,
            refetchFolders: refetch
          } satisfies AppHelperContextType}
        />
      }
    />
  )
}

export default AppCustomLayout;
