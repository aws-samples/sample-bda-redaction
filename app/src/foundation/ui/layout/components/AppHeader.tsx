// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { TopNavigation } from "@cloudscape-design/components";
import logoUrl from "../../../../assets/aws_logo.png";

function AppHeader() {
  return (
    <TopNavigation
      identity={{
        href: "#",
        title: "PII Redaction using Amazon Bedrock",
        logo: {
          src: logoUrl,
          alt: "Service"
        },
      }}
      utilities={[]}
    />
  )
}

export default AppHeader;