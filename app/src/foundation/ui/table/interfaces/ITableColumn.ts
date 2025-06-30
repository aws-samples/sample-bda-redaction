/*
 * © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 *
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement
 * available at http://aws.amazon.com/agreement or other written agreement between
 * Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import {ReactNode} from "react";
import {TableProps} from "@cloudscape-design/components";
import {ITableSortingType} from "./ITableSortingType";

export interface ITableColumn<T> extends TableProps.ColumnDefinition<T> {
    id: string;
    header: string;
    cell: (item: T) => ReactNode;
    sortingField?: string;
    sortOrder: number;
    visible: boolean;
    attributeSortOrder: number;
    ariaLabel?: ({sorted, descending, disabled}: ITableSortingType) => string;
    propertyFilteringOperators?: string[];
}
