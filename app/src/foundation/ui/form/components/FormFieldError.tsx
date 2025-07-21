// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { Box, Icon, SpaceBetween } from "@cloudscape-design/components";
import { colorChartsRed500 } from "@cloudscape-design/design-tokens";

interface IFormFieldErrorProps {
  errorMsg?: string;
}

function FormFieldError(props: IFormFieldErrorProps) {
  return (
    <SpaceBetween direction="horizontal" size="xxs">
      <Icon name="status-warning" variant="error" />
      <Box variant="small">
        <span style={{color: colorChartsRed500}}>{ props.errorMsg }</span>
      </Box>
    </SpaceBetween>
  )
}

export default FormFieldError;
