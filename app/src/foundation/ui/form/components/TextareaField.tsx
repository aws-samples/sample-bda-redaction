// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import {
  FormField,
  FormFieldProps,
  Textarea,
  TextareaProps,
} from "@cloudscape-design/components";
import { useController } from "react-hook-form";
import { ValidatedFormFieldProps } from "../types";

type TextareaFieldProps = TextareaProps & FormFieldProps & ValidatedFormFieldProps;

function TextareaField(props: TextareaFieldProps) {
  const {
    field: { onBlur, name, value, ref },
    // fieldState: { invalid, isTouched, isDirty },
    // formState: { touchedFields, dirtyFields }
  } = useController({
    name: props.name ?? props.fieldName,
    control: props.control,
    rules: props.validationRules,
    defaultValue: props.value
  });

  return (
    <FormField
      {...props}
      errorText={props.errors}
    >
      <Textarea
        {...props}
        key={name}
        value={value}
        name={name}
        ref={ref}
        onBlur={onBlur}
      />
    </FormField>
  )
}

export default TextareaField;
