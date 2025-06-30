import {Control} from "react-hook-form";

export type ValidatedFormFieldProps = {
  fieldName: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: Control<any>;
  errors?: string | undefined;
  validationRules?: {
      [key: string]: string | number | boolean;
  };
};