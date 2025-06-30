// © 2024 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { ReactNode, useEffect, useState } from "react";
import {
  Box,
  Button,
  CollectionPreferences,
  CollectionPreferencesProps,
  Header,
  Table,
  TableProps,
  Pagination,
  PropertyFilter,
  PropertyFilterProps,
  SpaceBetween,
  // TextFilter
} from "@cloudscape-design/components";
import { useCollection } from "@cloudscape-design/collection-hooks";
import EmptyState from "./EmptyState";
import { ITableColumn } from "../interfaces/ITableColumn";
import {
  paginationLabels,
  getMatchesCountText,
  contentDisplayPreferences,
  createLabelFunction,
  getVisibleColumns
} from "../libs/helpers";

interface DataTableProps<T> extends TableProps<T> {
  columnDefinitions: ITableColumn<T>[];
  columnDefinitionOverrides?: Record<string, unknown>;
  tableTitle: ReactNode;
  pageTitleHeaderType?: "h2" | "h3";
  resizeableColumns?: boolean;
  tableHeaderActions?: ReactNode;
  tableHeaderInfo?: ReactNode;
  tableFooter?: ReactNode;
  tableDescription?: ReactNode;
  collectionPreferencesProps?: object;
  defaultSortingColumn?: string;
  defaultSortingDescending?: boolean;
  enableTextFiltering?: boolean;
  excludePropertyFilteringFields?: string[];
  customColumnActions?: {
    [key: string]: {
      eventAction: (item: T) => void;
      buttonLabel: string;
    }
  }
  emitSelectedItems?: (items: readonly T[] | undefined) => void;
  refreshItems?: () => void;
}

const defaultPropertyQuery: PropertyFilterProps.Query = { tokens: [], operation: "or" };

function DataTable<T>(props: DataTableProps<T>) {
  const [propertyFilters, setPropertyFilters] = useState<PropertyFilterProps.FilteringProperty[]>([]);
  const [preferences, setPreferences] = useState<CollectionPreferencesProps.Preferences>({
    pageSize: 10,
    contentDisplay: getVisibleColumns(getColumnnDefinitions())
  });
  const { items, actions, filteredItemsCount, collectionProps, /* filterProps,*/ propertyFilterProps, paginationProps } = useCollection(
    props.items,
    {
      filtering: {
        empty: props.empty,
        noMatch: (
          <EmptyState
            title="No matches"
            action={<Button onClick={() => actions.setFiltering('')}>Clear filter</Button>}
          />
        ),
      },
      propertyFiltering: {
        filteringProperties: propertyFilters,
        empty: props.empty
      },
      pagination: {
        pageSize: preferences.pageSize
      },
      sorting: props.defaultSortingColumn
        ? {
            defaultState: {
              sortingColumn: {
                sortingField: props.defaultSortingColumn
              },
              isDescending: props.defaultSortingDescending ?? false
            }
          }
        : {},
      selection: {
        keepSelection: true
      },
    }
  );
  const { selectedItems, onSelectionChange, onSortingChange, sortingColumn, sortingDescending } = collectionProps;

  function getPropertyFilteringColumnConfig<T>(columnDefinitions: ITableColumn<T>[], excludedPropertyFilters?: string[]): PropertyFilterProps.FilteringProperty[] {
    return columnDefinitions
      .filter((column) => column.visible)
      .filter((column) => (excludedPropertyFilters) ? !excludedPropertyFilters?.includes(column.id) : true)
      .map((column) => {
        return {
          key: column.id,
          operators: column.propertyFilteringOperators,
          propertyLabel: column.header,
          groupValuesLabel: `${column.header} values`
        };
      })
      .sort((a, b) => a.key.localeCompare(b.key));
  }

  function preProcessColumnDefs(columnDefinitions: ITableColumn<T>[]) {
    columnDefinitions.forEach(columnDef => {
      if (props.columnDefinitionOverrides && props.columnDefinitionOverrides[columnDef.id]) {
        Object.assign(columnDef, props.columnDefinitionOverrides[columnDef.id]);
      }
    });

    props.columnDisplay?.forEach(columnDef => {
      if (props.columnDefinitionOverrides && props.columnDefinitionOverrides[columnDef.id]) {
        Object.assign(columnDef, props.columnDefinitionOverrides[columnDef.id]);
      }
    });
  }

  function getColumnnDefinitions() {
    if(props.customColumnActions) {
      const actionsColExists = props.columnDefinitions.filter(col => col.id === 'actions').length > 0;
      if(!actionsColExists) {
        props.columnDefinitions.push({
          id: 'actions',
          header: 'Actions',
          cell: item => {
            if(Object.keys(props.customColumnActions!).length > 1) {
              return (
                <SpaceBetween size="xs" direction="vertical">
                  {Object.keys(props.customColumnActions!).map(key => (
                    <Button
                      variant="normal"
                      onClick={() => props.customColumnActions![key].eventAction(item)}
                    >
                      {props.customColumnActions![key].buttonLabel}
                    </Button>
                  ))}
                </SpaceBetween>
              );
            } else {
              const key = Object.keys(props.customColumnActions!)[0];
              return (
                <Button
                  variant="normal"
                  onClick={() => props.customColumnActions![key].eventAction(item)}
                >
                  Enable/Disable
                </Button>
              )
            }
          },
          sortingField: 'actions',
          sortOrder: 1000,
          attributeSortOrder: 1000,
          visible: true,
          ariaLabel: createLabelFunction("actions"),
          propertyFilteringOperators: ["=", "!=", "^"],
        });
      }
    }

    return props.columnDefinitions;
  }

  useEffect(() => {
    preProcessColumnDefs(getColumnnDefinitions());
    setPropertyFilters(getPropertyFilteringColumnConfig(getColumnnDefinitions(), props.excludePropertyFilteringFields));
  }, []);

  return (
    <Table
      {...props}
      items={items}
      columnDisplay={preferences.contentDisplay}
      empty={props.empty ?? <EmptyState title={`No ${props.tableTitle}`} />}
      variant={props.variant ?? "full-page"}
      loadingText={props.loadingText ?? "Loading..."}
      resizableColumns={props.resizeableColumns ?? false}
      selectedItems={props.selectedItems ?? selectedItems}
      sortingColumn={sortingColumn}
      sortingDescending={sortingDescending}
      stickyColumns={props.stickyColumns ?? {first: 1, last: 0}}
      stripedRows={props.stripedRows ?? true}
      totalItemsCount={props.items?.length}
      header={
        <Header
          variant={props.pageTitleHeaderType ?? "h1" }
          counter={selectedItems?.length ? `(${selectedItems?.length})` : `(${props.items?.length})`}
          actions={[
            (props.refreshItems) ? <Box margin={"xs"}><Button iconName="refresh" onClick={props.refreshItems} /></Box> : <></>,
            props.tableHeaderActions
          ]}
          description={props.tableDescription}
          info={props.tableHeaderInfo}
        >
          {props.tableTitle}
        </Header>
      }
      footer={props.tableFooter}
      pagination={
        items.length > 0 && paginationProps &&
        <Pagination
          {...paginationProps}
          ariaLabels={paginationLabels}
        />
      }
      filter={
        items.length > 0 &&
        <PropertyFilter
          {...propertyFilterProps}
          filteringPlaceholder={`Find ${props.tableTitle}`}
          countText={getMatchesCountText(filteredItemsCount ?? 0)}
          filteringAriaLabel="Filter data"
          expandToViewport
          disableFreeTextFiltering={false}
          customFilterActions={
            <Button onClick={() => actions.setPropertyFiltering(defaultPropertyQuery)}>Clear filter(s)</Button>
          }
        />
      }
      preferences={
        items.length > 0 && props.collectionPreferencesProps &&
        <CollectionPreferences
          {...props.collectionPreferencesProps}
          preferences={preferences}
          contentDisplayPreference={contentDisplayPreferences(props.columnDefinitions)}
          onConfirm={({ detail }) => setPreferences(detail)}
        />
      }
      onSelectionChange={(e) => {
        if(props.onSelectionChange) props.onSelectionChange(e);
        else if(onSelectionChange) onSelectionChange(e);

        if(props.emitSelectedItems) props.emitSelectedItems(e.detail.selectedItems);
      }}
      onSortingChange={onSortingChange}
      /* filter={
        props.enableTextFiltering &&
        <TextFilter
          {...filterProps}
          countText={getMatchesCountText(filteredItemsCount ?? 0)}
          filteringPlaceholder="Begin typing to filter data displayed"
          filteringAriaLabel="Filter data"
        />
      } */
    />
  );
}

export default DataTable;
