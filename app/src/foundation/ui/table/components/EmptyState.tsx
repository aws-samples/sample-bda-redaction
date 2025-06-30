// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { ReactNode } from "react";
import { Box } from "@cloudscape-design/components";

interface EmptyStateProps {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
}

export default function EmptyState({ title, subtitle, action }: EmptyStateProps) {
  return (
    <Box textAlign="center" color="inherit">
      <Box variant="strong" textAlign="center" color="inherit">
        {title}
      </Box>
      {
      subtitle &&
        <Box variant="p" padding={{ bottom: 's' }} color="inherit">
          {subtitle}
        </Box>
      }
      <Box margin={{top: "s"}}>
        {action}
      </Box>
    </Box>
  );
}