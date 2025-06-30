import {
  Box,
  Button,
  SpaceBetween,
} from "@cloudscape-design/components";
import DateTimeDisplay from "./DateTimeDisplay";
import { Email } from "../types";

interface EmailOptionsProps {
  email: Email;
}

function EmailOptions(props: EmailOptionsProps) {
  return (
    <Box variant="div" padding={{top: "xxxl"}}>
      <SpaceBetween direction="vertical" size="xs">
        <Box variant="span"><strong>Date:</strong> <DateTimeDisplay datetime={ props.email.EmailReceiveTime } /></Box>
        <Button variant="inline-link" iconName="arrow-right" ariaLabel={`Open forward email modal for ${ props.email.EmailSubject }`}>Forward</Button>
      </SpaceBetween>
    </Box>
  )
}

export default EmailOptions;