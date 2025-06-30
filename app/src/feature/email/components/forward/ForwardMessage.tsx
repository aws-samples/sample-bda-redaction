// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { forwardRef, useImperativeHandle, useState } from "react";
import {
  Box,
  Button,
  Container,
  Form,
  Header,
  Modal,
  SpaceBetween,
  TokenGroup
} from "@cloudscape-design/components";
import { useForm } from "react-hook-form";
import { zodResolver } from '@hookform/resolvers/zod';
import { forwardMessageFormSchema } from "../../schemas/ForwardMessageFormSchema";
import TextField from "../../../../foundation/ui/form/components/TextField";
import { Email } from "../../../../foundation/email/types";
import { ModalOpenState } from "../../../../foundation/ui/types";
import FullEmailDisplay from "../../../../foundation/email/components/FullEmailDisplay";
import { useForwardMessage } from "../../hooks/UseForwardMessage";
import FormFieldError from "../../../../foundation/ui/form/components/FormFieldError";
import { useAppHelpers } from "../../../../foundation/ui/layout/libs/helpers";

interface ForwardMessageProps {
  email: Email;
}

type FormData = {
  emails: string[];
  email: string;
};

const ForwardMessage = forwardRef<ModalOpenState, ForwardMessageProps>((props, ref) => {
  const { control, handleSubmit, setValue, reset, getValues, trigger, formState: { errors } } = useForm<FormData>({
    mode: "onChange",
    reValidateMode: "onChange",
    criteriaMode: "all",
    delayError: 250,
    defaultValues: {
      emails: [],
      email: ""
    },
    resolver: zodResolver(forwardMessageFormSchema)
  });
  const [open, setOpen] = useState(false);
  const [emails, setEmails] = useState<string[]>([]);
  const { mutate, isPending } = useForwardMessage();
  const appHelpers = useAppHelpers();

  async function handleFormSubmit(data: FormData) {
    try {
      const body = {
        emails: (data.email.length > 0 && emails.length === 0) ? [data.email] : emails,
        case_id: props.email.CaseID
      };

      mutate(body, {
        onSuccess: () => {
          appHelpers.setNotifications([
            {
              type: "success",
              header: "Success!",
              content: `Email forwarded successfully.`
            }
          ]);
        },
        onError: () => {
          appHelpers.setNotifications([
            {
              type: "error",
              header: "Error!",
              content: `Not able to forward email.`
            }
          ]);
        },
        onSettled: () => {
          onModalDismissed();
        }
      });
    } catch (error) {
      console.error(error);
    } finally {
      onModalDismissed();
    }
  }

  function onModalDismissed() {
    setOpen(false);
    reset();
    setEmails([]);
  }

  useImperativeHandle(ref, () => ({
    setOpen(visible: boolean) {
      setOpen(visible);
    }
  }));

  return (
    <Modal
      visible={open}
      header="Forward Email"
      onDismiss={onModalDismissed}
      size="large"
    >
      <SpaceBetween direction="vertical" size="m">
        <Box variant="span">
          Use the form below to forward this email to the specified email address(es)
        </Box>

        <form onSubmit={handleSubmit(handleFormSubmit)}>
          <Form
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button variant="link" formAction="none" disabled={isPending} onClick={onModalDismissed}>Cancel</Button>
                <Button variant="primary" disabled={isPending} loading={isPending} formAction="submit">Forward</Button>
              </SpaceBetween>
            }
          >
            <TextField
              control={control}
              fieldName="email"
              label="Enter email address(es)"
              description="Separate multiple addresses with a comma"
              constraintText="Must be a valid email address or comma-separated list of email addresses"
              onChange={({ detail }) => setValue("email", detail.value) }
              onKeyUp={async ({ detail }) => {
                if(detail.key === "Enter" || detail.keyCode === 188) {
                  // remove trailing comma to prevent unnecessary email format validation failure
                  setValue("email", getValues("email").replace(",", ""));
                  const response = await trigger("email");

                  if(response) {
                    setEmails([...emails, getValues("email")]);
                    setValue("email", "");
                  }
                }
              }}
              onKeyDown={(event) => {
                // prevent enter key from closing modal when entering email addresses
                if(event.detail.key === "Enter") event.preventDefault();
              }}
              errors={errors.email?.message}
              value=""
            />

            <TokenGroup
              items={emails.map(email => ({
                label: email,
                dismissLabel: `Remove ${email}`
              }))}
              onDismiss={({ detail: { itemIndex } }) => {
                setEmails([
                  ...emails.slice(0, itemIndex),
                  ...emails.slice(itemIndex + 1)
                ]);
              }}
            />
            { errors.emails && <FormFieldError errorMsg={errors.emails?.message} /> }

            <br />
            <Container
              header={
                <Header
                  variant="h3"
                  description={ `Subject: ${props.email?.EmailSubject}`}
                >
                  Email Preview
                </Header>
              }
            >
              <FullEmailDisplay email={props.email} previewMode={true} />
            </Container>
          </Form>
        </form>
      </SpaceBetween>
    </Modal>
  );
});

export default ForwardMessage;
