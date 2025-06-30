import { DateRangePickerProps } from "@cloudscape-design/components";

export type RuleLineItem = {
  fieldName: string;
  fieldCondition?: string;
  fieldValue: string;
};

export type CreateRuleFormData = {
  folderId: string;
  ruleLineItems: RuleLineItem[];
  dateRange: DateRangePickerProps.AbsoluteValue;
  description: string;
  conditions?: string;
}

export type Rule = {
  ID: string;
  FolderID: string;
  FolderName: string;
  Criteria: string;
  Description: string;
  Enabled: string;
  Creator: string;
  CreatedAt: string;
}