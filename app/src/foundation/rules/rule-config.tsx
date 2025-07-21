// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import moment from "moment";
import { ITableColumn } from "../ui/table/interfaces/ITableColumn";
import {
  createLabelFunction,
  pageSizePreference,
  contentDisplayPreferences,
} from "../ui/table/libs/helpers";
import { Rule, RuleLineItem } from "./types";
import { Box } from "@cloudscape-design/components";

const columnDefinitions: ITableColumn<Rule>[] = [
  {
    id: 'Description',
    header: 'Description',
    cell: item => item.Description,
    sortingField: 'Description',
    isRowHeader: true,
    sortOrder: 20,
    attributeSortOrder: 20,
    visible: true,
    ariaLabel: createLabelFunction("description"),
    propertyFilteringOperators: ["=", "!=", ":", "!:"],
  },
  {
    id: 'Criteria',
    header: 'Rule Criteria',
    cell: item => (
      <Box variant="p">
        {
          JSON.parse(item.Criteria)?.map((c: RuleLineItem) => {
            return (
              <>
                <Box variant="span">
                  {getReadableFieldName(c.fieldName)} {c.fieldCondition} {c.fieldValue}
                </Box>
                <br />
              </>
            )
          })
        }
      </Box>
    ),
    sortingField: 'Criteria',
    isRowHeader: true,
    sortOrder: 30,
    attributeSortOrder: 30,
    visible: true,
    ariaLabel: createLabelFunction("criteria"),
    propertyFilteringOperators: ["=", "!=", ":", "!:"],
  },
  {
    id: 'FolderName',
    header: 'Folder',
    cell: item => item.FolderName,
    sortingField: 'FolderName',
    sortOrder: 40,
    attributeSortOrder: 40,
    visible: true,
    ariaLabel: createLabelFunction("name"),
    propertyFilteringOperators: ["=", "!=", ":", "!:"],
  },
  {
    id: 'Creator',
    header: 'Creator',
    cell: item => item.Creator,
    sortingField: 'Creator',
    sortOrder: 50,
    attributeSortOrder: 50,
    visible: true,
    ariaLabel: createLabelFunction("creator"),
    propertyFilteringOperators: ["=", "!=", ":", "!:"],
  },
  {
    id: 'CreatedAt',
    header: 'Created At',
    cell: item => {
      const formattedDate = item.CreatedAt?.split("+")[0];
      return moment(formattedDate).format("L LT")
    },
    sortingField: 'CreatedAt',
    sortOrder: 60,
    attributeSortOrder: 60,
    visible: true,
    ariaLabel: createLabelFunction("created_at"),
    propertyFilteringOperators: ["=", "!="],
  },
  // {
  //   id: 'enabled',
  //   header: 'Enabled',
  //   cell: item => (item.Enabled) ? 'Yes' : 'No',
  //   sortingField: 'enabled',
  //   sortOrder: 70,
  //   attributeSortOrder: 70,
  //   visible: true,
  //   ariaLabel: createLabelFunction("enabled"),
  //   propertyFilteringOperators: ["=", "!=", ":", "!:"],
  // }
];

const collectionPreferencesProps = {
  pageSizePreference,
  contentDisplayPreferences: contentDisplayPreferences(columnDefinitions),
  cancelLabel: 'Cancel',
  confirmLabel: 'Confirm',
  title: 'Folders Table Display Preferences',
};

const getReadableFieldName = (fieldName: string): string => {
  switch(fieldName) {
    case 'RedactedBody':
      return 'Body';
    case 'EmailSubject':
      return 'Subject';
    case 'FromAddress':
      return 'From';
    case 'sent_date':
      return 'Date Received';
    default:
      return '';
  }
};

export {
  columnDefinitions,
  collectionPreferencesProps,
};
