/*
 * © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
 *
 * This AWS Content is provided subject to the terms of the AWS Customer Agreement
 * available at http://aws.amazon.com/agreement or other written agreement between
 * Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
 */

import {CollectionPreferencesProps} from "@cloudscape-design/components";
import {ITableSortingType} from "../interfaces/ITableSortingType";
import {ITableColumn} from "../interfaces/ITableColumn";

const paginationLabels = {
    nextPageLabel: "Next page",
    pageLabel: (pageNumber: number) => `Go to page ${pageNumber}`,
    previousPageLabel: "Previous page"
};

const pageSizePreference = {
    title: "Select page size",
    options: [
        {value: 10, label: "10 resources"},
        {value: 20, label: "20 resources"},
        {value: 50, label: "50 resources"},
        {value: 100, label: "100 resources"}
    ]
};

function contentDisplayPreferences<T>(
    columnDefinitions: ITableColumn<T>[]
): CollectionPreferencesProps.ContentDisplayPreference {
    return {
        title: "Column preferences",
        description: "Customize the columns visibility and order.",
        options: columnDefinitions.map(({id, header}) => ({
            id,
            label: header,
            alwaysVisible: false
        }))
    };
}

function createLabelFunction(
    columnName: string
): ({sorted, descending}: ITableSortingType) => string {
    return ({sorted, descending}: ITableSortingType) => {
        const sortState = sorted
            ? `sorted ${descending ? "descending" : "ascending"}`
            : "not sorted";
        return `${columnName}, ${sortState}.`;
    };
}

function getMatchesCountText(count: number): string {
    return count === 1 ? `${count} match` : `${count} matches`;
}

function getVisibleColumns<T>(columnDefinitions: ITableColumn<T>[]) {
    return columnDefinitions
        .sort((a, b) => a.sortOrder - b.sortOrder)
        .map((column) => {
            return {
                id: column.id,
                visible: column.visible
            };
        });
}

export {
    paginationLabels,
    pageSizePreference,
    contentDisplayPreferences,
    createLabelFunction,
    getMatchesCountText,
    getVisibleColumns,
};
