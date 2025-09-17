// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { useState } from 'react';
import {
  AppLayout,
  AppLayoutProps,
  BreadcrumbGroup,
  Flashbar,
  FlashbarProps,
  SideNavigation,
} from '@cloudscape-design/components';
import { Outlet, useMatches, useNavigate } from 'react-router-dom';
import { AppHelperContextType } from '../types';

type RouteMatchHandle = {
  crumb: (name: string) => string;
}

function AppCustomLayout() {
  const navigate = useNavigate();
  const routeMatches = useMatches();
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
          } satisfies AppHelperContextType}
        />
      }
    />
  )
}

export default AppCustomLayout;
