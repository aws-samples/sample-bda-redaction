// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import {
  FormField,
  FormFieldProps,
  Select,
  SelectProps,
} from "@cloudscape-design/components";
import { useController } from "react-hook-form";
import { ValidatedFormFieldProps } from "../types";

type SelectFieldProps = SelectProps & FormFieldProps & ValidatedFormFieldProps;

function SelectField(props: SelectFieldProps) {
  const {
    field: { onBlur, name, ref },
    // fieldState: { invalid, isTouched, isDirty },
    // formState: { touchedFields, dirtyFields }
  } = useController({
    name: props.name ?? props.fieldName,
    control: props.control,
    rules: props.validationRules,
    defaultValue: props.selectedOption
  });

  return (
    <FormField
      {...props}
      errorText={props.errors}
    >
      <Select
        {...props}
        key={name}
        ref={ref}
        selectedOption={props.selectedOption}
        onBlur={onBlur}
      />
    </FormField>
  )
}

export default SelectField;
