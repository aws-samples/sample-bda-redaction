import {
  Box,
  Grid,
} from "@cloudscape-design/components";
import { Email } from "../types";
import DateTimeDisplay from "./DateTimeDisplay";

interface EmailPreviewBodyProps {
  email: Email;
  numOfChars?: number;
}

const NUM_OF_CHARS: number = 100;

function EmailPreviewBody(props: EmailPreviewBodyProps) {
  const truncateAtLastSpace = (str: string, length: number, ending: string = ' ...') => {
    if (str.length <= length) return str;
    let trimmedString = str.slice(0, length + 1);
    return trimmedString.slice(0, Math.min(trimmedString.length, trimmedString.lastIndexOf(' '))) + ending;
  }

  return (
    <Grid gridDefinition={[{colspan: 10}, {colspan: 2}]}>
      <Box variant="div">{ truncateAtLastSpace(props.email.EmailBody, props.numOfChars ?? NUM_OF_CHARS) }</Box>
      <Box variant="div" float="right">
        <DateTimeDisplay datetime={props.email.EmailReceiveTime} />
      </Box>
    </Grid>
  )
}

export default EmailPreviewBody;