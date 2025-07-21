// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import {
  DateRangePicker,
  DateRangePickerProps,
  FormField,
  FormFieldProps,
} from "@cloudscape-design/components";
import { useController } from "react-hook-form";
import { ValidatedFormFieldProps } from "../types";

type DateRangePickerFieldProps = DateRangePickerProps & FormFieldProps & ValidatedFormFieldProps;

function DateRangePickerField(props: DateRangePickerFieldProps) {
  const {
    field: { onBlur, name/* , ref */ },
    // fieldState: { invalid, isTouched, isDirty },
    // formState: { touchedFields, dirtyFields }
  } = useController({
    name: props.fieldName,
    control: props.control,
    rules: props.validationRules,
    defaultValue: props.value
  });

  return (
    <FormField
      {...props}
      errorText={props.errors}
    >
      <DateRangePicker
        {...props}
        key={name}
        onBlur={onBlur}
      />
    </FormField>
  )
}

export default DateRangePickerField;
