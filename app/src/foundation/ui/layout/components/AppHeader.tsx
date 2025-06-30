// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { TopNavigation } from "@cloudscape-design/components";
import { useAuth } from "react-oidc-context";
import logoUrl from "../../../../assets/aws_logo.png";

function AppHeader() {
  const auth = useAuth();

  const getLogoutUrl = () => {
    const returnUrl = (import.meta.env.VITE_OIDC_LOGOUT_RETURN_URL !== "")
      ? import.meta.env.VITE_OIDC_LOGOUT_RETURN_URL
      : window.location.origin + import.meta.env.VITE_BASE;

    if(import.meta.env.VITE_OIDC_LOGOUT_URL === undefined || import.meta.env.VITE_OIDC_LOGOUT_URL === "") {
      return returnUrl;
    }

    return `${import.meta.env.VITE_OIDC_LOGOUT_URL}?retURL=${returnUrl}`
  }

  return (
    <TopNavigation
      identity={{
        href: "#",
        title: "AT&T Office of the President Email Compliance Intake Platform Portal",
        logo: {
          src: logoUrl,
          alt: "Service"
        },
      }}
      utilities={[
        {
          type: "button",
          text: "Logout",
          onClick: () => {
            void auth.signoutRedirect({
              post_logout_redirect_uri: getLogoutUrl(),
              redirectTarget: "self"
            });
          }
        },
        {
          type: "menu-dropdown",
          text: (auth.isAuthenticated) ? `${auth.user?.profile?.given_name} ${auth.user?.profile?.family_name}` : 'Unknown User',
          description: (auth.isAuthenticated) ? `${auth.user?.profile.user_alias}` : 'unknown',
          iconName: "user-profile",
          items: []
        }
      ]}
    />
  )
}

export default AppHeader;