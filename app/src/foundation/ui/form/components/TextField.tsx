// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import {
  FormField,
  FormFieldProps,
  Input,
  InputProps,
} from "@cloudscape-design/components";
import { useController } from "react-hook-form";
import { ValidatedFormFieldProps } from "../types";

type TextFieldProps = InputProps & FormFieldProps & ValidatedFormFieldProps;

function TextField(props: TextFieldProps) {
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
      <Input
        {...props}
        key={name}
        name={name}
        value={value}
        ref={ref}
        onBlur={onBlur}
      />
    </FormField>
  )
}

export default TextField;
