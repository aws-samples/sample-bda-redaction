// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import {
  Button,
  ButtonProps
} from "@cloudscape-design/components";
import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useAppHelpers } from "../layout/libs/helpers";

interface RoutedButtonProps extends ButtonProps {
  buttonText: ReactNode;
  stateData?: object;
}

function RoutedButton(props: RoutedButtonProps) {
  const navigate = useNavigate();
  const outletCtx = useAppHelpers();

  function onClickHandler(href?: string) {
    if(href) {
      outletCtx.setNotifications([]);
      navigate(href, { state: props.stateData});
    }
  }

  return (
    <Button
      {...props}
      onClick={(e) => {
        e.preventDefault();
        if(props.onClick) props.onClick(e);
        onClickHandler(`${props.href}`)
      }}
    >
      { props.buttonText }
    </Button>
  )
}

export default RoutedButton;
