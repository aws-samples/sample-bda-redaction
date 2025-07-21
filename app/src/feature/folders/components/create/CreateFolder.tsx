// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { useEffect } from "react";
import {
  Button,
  Form,
  Header,
  SpaceBetween,
} from "@cloudscape-design/components";
import { useForm } from "react-hook-form";
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from "react-router-dom";
import { useAppHelpers } from "../../../../foundation/ui/layout/libs/helpers";
import { createFolderFormSchema } from "../../schemas/CreateFolderFormSchema";
import { useCreateFolder } from "../../hooks/UseCreateFolder";
import TextField from "../../../../foundation/ui/form/components/TextField";
import TextareaField from "../../../../foundation/ui/form/components/TextareaField";
import RoutedButton from "../../../../foundation/ui/buttons/RoutedButton";

type FormData = {
  name: string;
  description: string;
};

function CreateFolder() {
  const { control, handleSubmit, setValue, formState: { errors } } = useForm<FormData>({
    mode: "all",
    reValidateMode: "onChange",
    criteriaMode: "all",
    delayError: 250,
    defaultValues: {
      name: "",
      description: "",
    },
    resolver: zodResolver(createFolderFormSchema)
  });
  const { mutate, isPending } = useCreateFolder();
  const outletCtx = useAppHelpers();
  const navigate = useNavigate();

  async function handleFormSubmit(data: FormData) {
    const body = {
      Name: data.name,
      Description: data.description,
    };

    mutate(body, {
      onSuccess: (data) => {
        outletCtx.setNotifications([
          {
            type: "success",
            header: "Success!",
            content: `Folder ${data.Name} was created successfully`
          }
        ]);
        navigate(`${import.meta.env.VITE_BASE}/folders`, {replace: true});
      },
      onError: (error) => {
        console.error("Error creating folder:", error);
        outletCtx.setNotifications([
          {
            type: "error",
            header: "Error!",
            content: `Not able to create folder`,
          }
        ]);
      }
    });
  }

  useEffect(() => {
    outletCtx.setActiveDrawerId("");
    outletCtx.setActiveDrawer([]);
  }, []);

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)}>
      <Form
        header={
          <Header variant="h1" description="Use the form below to create a new folder that emails can be added to for better message organization.">
            Create New Folder
          </Header>
        }
        actions={
          <SpaceBetween direction="horizontal" size="xs">
            <RoutedButton
              variant="link"
              formAction="none"
              buttonText="Cancel"
              href=".."
              disabled={isPending}
            />
            <Button variant="primary" disabled={isPending} loading={isPending} formAction="submit">Add Folder</Button>
          </SpaceBetween>
        }
        errorText={Object.entries(errors).length > 0 ? "Please correct the errors displayed in the form" : null}
      >
        <SpaceBetween direction="vertical" size="m">
          <TextField
            control={control}
            fieldName="name"
            label="Name of folder"
            onChange={({ detail }) => setValue("name", detail.value) }
            errors={errors.name?.message}
            value=""
          />

          <TextareaField
            control={control}
            fieldName="description"
            label={
              <span>Folder Description <i>- optional</i></span>
            }
            onChange={(e) => setValue("description", e.detail.value)}
            rows={5}
            value=""
          />
        </SpaceBetween>
      </Form>
    </form>
  );
};

export default CreateFolder;
