// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import {
  AttributeEditor,
  Button,
  Container,
  DateRangePickerProps,
  Form,
  Header,
  SpaceBetween
} from "@cloudscape-design/components";
import RoutedButton from "../../../../foundation/ui/buttons/RoutedButton";
import { useNavigate } from "react-router-dom";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from '@hookform/resolvers/zod';
import TextField from "../../../../foundation/ui/form/components/TextField";
import DateRangePickerField from "../../../../foundation/ui/form/components/DateRangePickerField";
import SelectField from "../../../../foundation/ui/form/components/SelectField";
import FormFieldError from "../../../../foundation/ui/form/components/FormFieldError";
import { createRuleFormSchema } from "../../schemas/CreateRuleFormSchema";
import { useGetFolders } from "../../../folders/hooks/UseGetFolders";
import { useCreateRule } from "../../hooks/UseCreateRule";
import { Folder } from "../../../../foundation/folders/types";
import { getSelectOption } from "../../../../foundation/ui/form/libs/helpers";
import { CreateRuleFormData } from "../../../../foundation/rules/types";
import { useAppHelpers } from "../../../../foundation/ui/layout/libs/helpers";

function CreateRule() {
  const navigate = useNavigate();
  const outletCtx = useAppHelpers();
  const { control, handleSubmit, setValue, watch, formState: { errors } } = useForm<CreateRuleFormData>({
    mode: "all",
    reValidateMode: "onChange",
    criteriaMode: "all",
    delayError: 250,
    defaultValues: {
      folderId: "",
      ruleLineItems: [{ fieldName: "", fieldCondition: "", fieldValue: "" }],
      dateRange: {},
      description: "",
      conditions: ""
    },
    resolver: zodResolver(createRuleFormSchema)
  });
  const ruleLineItems = useFieldArray({
    control,
    name: "ruleLineItems" as never,
  });
  const folders = useGetFolders();
  const { mutate, isPending } = useCreateRule();

  const filterOptions = [
    {
      label: "From",
      value: "FromAddress",
    },
    {
      label: "Subject",
      value: "EmailSubject",
    },
    {
      label: "Body",
      value: "RedactedBody",
    },
    {
      label: "Has Attachments",
      value: "has_attachments",
    }
  ];

  const filterConditions = [
    {
      label: "Equals",
      value: "equals",
    },
    {
      label: "Contains",
      value: "contains",
    }
  ]

  async function handleFormSubmit(data: CreateRuleFormData) {
    delete(data['conditions']);
    mutate(data, {
      onSuccess: (data) => {
        outletCtx.setNotifications([
          {
            type: "success",
            header: "Success!",
            content: `Rule ${data.description} was created successfully`
          }
        ]);
        outletCtx.refetchFolders();
        navigate(`${import.meta.env.VITE_BASE}/rules`, {replace: true});
      },
      onError: (error) => {
        console.error("Error creating rule:", error);
        outletCtx.setNotifications([
          {
            type: "error",
            header: "Error!",
            content: `Not able to create rule`,
          }
        ]);
      }
    });
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)}>
      <Form
        header={
          <Header variant="h1" description="Use the form below to create a new email filtering rule to move emails to the selected folder.">
            Create New Email Filtering Rule
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
            <Button variant="primary" formAction="submit" loading={isPending} disabled={isPending}>Create Rule</Button>
          </SpaceBetween>
        }
        errorText={Object.entries(errors).length > 0 ? "Please correct the errors displayed in the form" : null}
      >
        <SpaceBetween direction="vertical" size="l">
          <Container
            header={
              <Header variant="h2">
                Details
              </Header>
            }
          >
            <TextField
              control={control}
              fieldName="description"
              label="Email Filtering Rule Description"
              description="Enter a description for this email message filtering rule"
              onChange={({ detail }) => setValue("description", detail.value)}
              errors={errors?.description?.message}
              value=""
            />
          </Container>

          <Container header={
            <Header variant="h2">
              When a new message arrives that meets all these conditions:
            </Header>
          }>
            <SpaceBetween direction="vertical" size="l">
              { errors.conditions && <FormFieldError errorMsg={errors.conditions?.message} /> }

              <AttributeEditor
                onAddButtonClick={() => ruleLineItems.append({})}
                onRemoveButtonClick={({detail: { itemIndex }}) => ruleLineItems.remove(itemIndex)}
                items={watch("ruleLineItems")}
                addButtonText="Add New Filter Option"
                removeButtonText="Remove"
                definition={[
                  {
                    label: "Select filter",
                    control: (_, itemIdx) => (
                      <SelectField
                        control={control}
                        fieldName={`ruleLineItems.${itemIdx}.fieldName` as const}
                        placeholder="Select filter"
                        options={filterOptions}
                        onChange={({ detail }) => {
                          setValue(`ruleLineItems.${itemIdx}.fieldName`, detail.selectedOption?.value ?? "");
                        }}
                        errors={errors?.ruleLineItems?.[itemIdx]?.fieldName ? errors?.ruleLineItems?.[itemIdx]?.fieldName?.message : ""}
                        selectedOption={getSelectOption(watch(`ruleLineItems.${itemIdx}.fieldName`), filterOptions)}
                      />
                    )
                  },
                  {
                    label: "Condition",
                    control: (_, itemIdx) => {
                      const conditions =
                        (watch(`ruleLineItems.${itemIdx}.fieldName`) === "RedactedBody")
                        ? filterConditions.filter(condition => condition.value !== 'equals')
                        : filterConditions;

                      return <SelectField
                        control={control}
                        fieldName={`ruleLineItems.${itemIdx}.fieldCondition` as const}
                        placeholder="Select condition"
                        options={conditions}
                        onChange={({ detail }) => {
                          setValue(`ruleLineItems.${itemIdx}.fieldCondition`, detail.selectedOption?.value ?? "");
                        }}
                        errors={errors?.ruleLineItems?.[itemIdx]?.fieldCondition ? errors?.ruleLineItems?.[itemIdx]?.fieldCondition?.message : ""}
                        selectedOption={getSelectOption(watch(`ruleLineItems.${itemIdx}.fieldCondition`), conditions)}
                        disabled={watch(`ruleLineItems.${itemIdx}.fieldName`) === "sent_date"}
                      />
                    }
                  },
                  {
                    label: "Filter value",
                    control: (_, itemIdx) => (
                      <TextField
                        control={control}
                        fieldName={`ruleLineItems.${itemIdx}.fieldValue` as const}
                        placeholder="Filter value"
                        onChange={({ detail }) => setValue(`ruleLineItems.${itemIdx}.fieldValue`, detail.value)}
                        errors={errors?.ruleLineItems?.[itemIdx]?.fieldValue ? errors?.ruleLineItems?.[itemIdx]?.fieldValue?.message : ""}
                        value=""
                      />
                    )
                  }
                ]}
              />
              {/* { errors?.ruleLineItems?.root && <FormFieldError errorMsg={errors?.ruleLineItems?.root?.message} /> } */}

              <DateRangePickerField
                control={control}
                fieldName="dateRange"
                label={
                  <span>Date range is between <i>- optional</i></span>
                }
                placeholder="Click here to display calendar"
                errors={errors.dateRange?.message}
                isValidRange={() => ({valid: true})}
                value={watch("dateRange")}
                relativeOptions={[]}
                rangeSelectorMode="absolute-only"
                dateOnly
                showClearButton
                onChange={({detail}) => setValue("dateRange", detail.value as DateRangePickerProps.AbsoluteValue) }
              />
            </SpaceBetween>
          </Container>

          <Container header={
            <Header variant="h2">
              Do the following:
            </Header>
          }>
            <SelectField
              control={control}
              fieldName="folderId"
              label="Move to folder"
              placeholder="Select a folder"
              empty="There are no folders available to select"
              options={folders.data?.map((folder: Folder) => {
                return {
                  label: folder.Name,
                  value: folder.ID,
                }
              })}
              onChange={({ detail }) => {
                setValue("folderId", detail.selectedOption?.value ?? "");
              }}
              errors={errors.folderId?.message}
              selectedOption={getSelectOption(watch("folderId"), folders.data?.map((folder: Folder) => {
                return {
                  label: folder.Name,
                  value: folder.ID,
                }
              }))}
            />
          </Container>
        </SpaceBetween>
      </Form>
    </form>
  );
}

export default CreateRule;
