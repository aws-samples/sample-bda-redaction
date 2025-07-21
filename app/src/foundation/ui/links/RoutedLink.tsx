// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  Link,
  LinkProps
} from "@cloudscape-design/components";
import { useAppHelpers } from "../layout/libs/helpers";

interface RoutedLinkProps extends LinkProps {
  buttonText: ReactNode;
  stateData?: object;
}

function RoutedLink(props: RoutedLinkProps) {
  const navigate = useNavigate();
  const outletCtx = useAppHelpers();

  const onFollowHandler = (href?: string) => {
    if(href) {
      outletCtx.setNotifications([]);
      navigate(href, {replace: true, state: props.stateData });
    }
  }

  return (
    <Link
      {...props}
      onFollow={(e) => {
        e.preventDefault();
        onFollowHandler(`${e.detail.href}`)
      }}
    >
      { props.buttonText }
    </Link>
  )
}

export default RoutedLink;
