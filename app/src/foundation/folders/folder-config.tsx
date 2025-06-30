// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
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
import { Folder } from "./types";

const columnDefinitions: ITableColumn<Folder>[] = [
  {
    id: 'Name',
    header: 'Name',
    cell: item => item.Name,
    sortingField: 'Name',
    isRowHeader: true,
    sortOrder: 20,
    attributeSortOrder: 20,
    visible: true,
    ariaLabel: createLabelFunction("name"),
    propertyFilteringOperators: ["=", "!=", ":", "!:"],
  },
  {
    id: 'Description',
    header: 'Description',
    cell: item => item.Description,
    sortingField: 'Description',
    sortOrder: 30,
    attributeSortOrder: 30,
    visible: true,
    maxWidth: 500,
    ariaLabel: createLabelFunction("description"),
    propertyFilteringOperators: ["=", "!=", ":", "!:"],
  },
  {
    id: 'Creator',
    header: 'Creator',
    cell: item => item.Creator,
    sortingField: 'Creator',
    sortOrder: 40,
    attributeSortOrder: 40,
    visible: true,
    ariaLabel: createLabelFunction("creator"),
    propertyFilteringOperators: ["=", "!=", ":", "!:"],
  },
  {
    id: 'CreatedAt',
    header: 'Created',
    cell: item => {
      const formattedDate = item.CreatedAt?.split("+")[0];
      return moment(formattedDate).format("L LT")
    },
    sortingField: 'CreatedAt',
    sortOrder: 50,
    attributeSortOrder: 50,
    visible: true,
    ariaLabel: createLabelFunction("created_at"),
    propertyFilteringOperators: ["=", "!="],
  }
];

const collectionPreferencesProps = {
  pageSizePreference,
  contentDisplayPreferences: contentDisplayPreferences(columnDefinitions),
  cancelLabel: 'Cancel',
  confirmLabel: 'Confirm',
  title: 'Folders Table Display Preferences',
};

export {
  columnDefinitions,
  collectionPreferencesProps,
};
