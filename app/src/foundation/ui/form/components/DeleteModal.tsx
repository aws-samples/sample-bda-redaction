// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { ReactNode, useState, forwardRef, useImperativeHandle } from "react";
import {
  Alert,
  Box,
  Button,
  Form,
  Modal,
  SpaceBetween
} from "@cloudscape-design/components";
import { useForm } from "react-hook-form";
import TextField from "./TextField";
import { ModalOpenState } from "../../types";

interface DeleteModalProps {
  modalHeader: ReactNode;
  entityName: string;
  entityType: "folder" | "rule";
  formSubmitLoading: boolean;
  handleFormSubmit: (data: FormData) => void;
}

type FormData = {
  confirm: string;
}

const DeleteModal = forwardRef<ModalOpenState, DeleteModalProps>((props, ref) => {
  const { control, handleSubmit, setValue, reset, watch, formState: { errors } } = useForm<FormData>({
    mode: "onChange",
    reValidateMode: "onChange",
    criteriaMode: "all",
    delayError: 250,
    defaultValues: {
      confirm: ""
    }
  });
  const watchConfirm = watch("confirm");
  const [open, setOpen] = useState(false);

  function onModalDismissed() {
    setOpen(false);
    reset();
  }

  useImperativeHandle(ref, () => ({
    setOpen(visible: boolean) {
      setOpen(visible);
      reset();
    }
  }));

  return (
    <Modal
      visible={open}
      header={props.modalHeader}
      onDismiss={onModalDismissed}
    >
      <SpaceBetween direction="vertical" size="m">
        <Box variant="span">
          Permanently delete { props.entityType } <strong>{ props.entityName }</strong>? You can’t undo this action.
        </Box>

        <Alert type="info">
          Deleting this folder <strong>will not</strong> delete the emails that are stored in it. They will be re-assigned to the General Inbox folder
        </Alert>

        <Box variant="span">
          To avoid accidental actions of this type, we ask you to provide additional written consent.
        </Box>

        <form onSubmit={handleSubmit(props.handleFormSubmit)}>
          <Form
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="link"
                  formAction="none"
                  onClick={onModalDismissed}
                  disabled={props.formSubmitLoading}
                >
                  Cancel
                </Button>

                <Button
                  variant="primary"
                  formAction="submit"
                  disabled={watchConfirm !== "delete me" || props.formSubmitLoading}
                  loading={props.formSubmitLoading}
                >
                  Delete { props.entityType.charAt(0).toUpperCase() + props.entityType.slice(1) }
                </Button>
              </SpaceBetween>
            }
          >
            <TextField
              control={control}
              fieldName="confirm"
              label={`To confirm this action, type "delete me".`}
              onChange={({ detail }) => setValue("confirm", detail.value)}
              errors={errors.confirm?.message}
              value=""
            />
          </Form>
        </form>
      </SpaceBetween>
    </Modal>
  );
})

export default DeleteModal;
