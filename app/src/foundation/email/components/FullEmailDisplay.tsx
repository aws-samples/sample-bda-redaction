import {
  Box,
  Button,
  Grid,
  Header,
  Icon,
  Link,
  SpaceBetween,
  Spinner,
  TextContent
} from "@cloudscape-design/components";
import DateTimeDisplay from "./DateTimeDisplay";
import RoutedLink from "../../ui/links/RoutedLink";
import { Email } from "../types";

interface FullEmailDisplayProps {
  email?: Email;
  isLoading?: boolean;
  hasError?: boolean;
  previewMode?: boolean;
  onForwardEmail?: () => void;
}

function FullEmailDisplay(props: FullEmailDisplayProps) {
  return (
    <Box variant="div" {...(!props.previewMode ? {padding:{horizontal: 'xxxl', vertical: 'xxxl'}} : {})}>
      {
        props.isLoading
        ?
          <Spinner size="large" variant="normal" />
        :
          <>
            {
              !props.previewMode &&
              <><br /><br /></>
            }
            <Grid gridDefinition={[{colspan: 9}, {colspan: 3}]}>
              <Box variant="div">
                {
                  !props.previewMode &&
                  <>
                    <Header
                      variant="h3"
                      description={
                        <Box variant="span" fontSize="heading-s" fontWeight="bold">Case ID: { props.email?.CaseID }</Box>
                      }
                    >
                      <Box variant="span" fontWeight="bold" fontSize="heading-xl">{ props.email?.EmailSubject }</Box>
                    </Header>
                  </>
                }
                <Box variant="div" margin={{top: "s", bottom: "xs"}}>
                  <SpaceBetween direction="horizontal" size="xxs">
                    <Icon name="envelope" variant="subtle" />
                    <Box variant="span"><strong>From:</strong> { props.email?.FromAddress }</Box>
                  </SpaceBetween>
                </Box>
                <Box variant="div">
                  <SpaceBetween direction="horizontal" size="xxs">
                    <Icon name="folder" variant="subtle" />
                    <Box variant="span"><strong>Folder: </strong>
                      {
                        !props.previewMode
                        ?
                          <RoutedLink href={`/folders/${props.email?.FolderID}`} variant="secondary" buttonText={props.email?.folder?.Name} />
                        :
                          <span>{ props.email?.folder?.Name }</span>
                      }
                    </Box>
                  </SpaceBetween>
                </Box>
              </Box>

              <Box variant="div" padding={{top: (props.previewMode) ? "xs" : "xxxl"}}>
                <SpaceBetween direction="vertical" size="xs">
                  <Box variant="span"><strong>Date:</strong> <DateTimeDisplay datetime={ props.email?.EmailReceiveTime } /></Box>
                  {
                    !props.previewMode &&
                    <Button variant="inline-link" iconName="arrow-right" onClick={props.onForwardEmail} ariaLabel={`Open forward email modal for ${props.email?.EmailSubject}`}>Forward</Button>
                  }
                </SpaceBetween>
              </Box>
            </Grid>
            <br />

            <div style={{whiteSpace: "pre-line"}}>{ props.email?.RedactedBody }</div>

            {
              props.email?.files?.length! > 0 &&
              <>
                <hr style={{marginTop: "1.5rem", marginBottom: "1.5rem", border: "1px solid #999"}} />

                <h4><Box variant="span" fontSize="heading-xl" fontWeight="bold">Attachments ({props.email?.files?.length!})</Box></h4>
                <TextContent>
                  <ul style={{listStyle: "none", padding: 0}}>
                    {
                      props.email?.files?.map((file, idx) => {
                        return (
                          <li style={{marginBottom: "0.25rem"}} key={idx.toString()}>
                            <SpaceBetween direction="horizontal" size="xxs">
                              <Icon name="file" variant="link" />
                              <Link href={ file.url } external>{ file.name }</Link>
                            </SpaceBetween>
                          </li>
                        )
                      })
                    }
                  </ul>
                </TextContent>
                <br />
              </>
            }
          </>
      }
    </Box>
  )
}

export default FullEmailDisplay;