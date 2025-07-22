// © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
//
// This AWS Content is provided subject to the terms of the AWS Customer Agreement
// available at http://aws.amazon.com/agreement or other written agreement between
// Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.

import { useState, useRef, useEffect, ReactNode } from "react";
import {
  Box,
  Button,
  // Calendar,
  Cards,
  // DatePicker,
  // DateInput,
  // FormField,
  Header,
  PropertyFilter,
  PropertyFilterProps,
  SpaceBetween,
  AppLayoutProps,
  Spinner,
} from "@cloudscape-design/components";
import { useCollection } from "@cloudscape-design/collection-hooks";
import { useParams } from "react-router-dom";
import EmailPreviewBody from "../../../../foundation/email/components/EmailPreviewBody";
import FullEmailDisplay from "../../../../foundation/email/components/FullEmailDisplay";
import { Email } from "../../../../foundation/email/types";
import EmptyState from "../../../../foundation/ui/table/components/EmptyState";
import { getMatchesCountText } from "../../../../foundation/ui/table/libs/helpers";
import { ModalOpenState } from "../../../../foundation/ui/types";
import { useGetMessages } from "../../hooks/UseGetMessages";
import { useGetMessage } from "../../hooks/UseGetMessage";
import { useGetFolder } from "../../../folders/hooks/UseGetFolder";
import { useExportMessage } from "../../hooks/UseExportMessages";
import { useAppHelpers } from "../../../../foundation/ui/layout/libs/helpers";
import ForwardEmail from "../forward/ForwardMessage";
import RoutedButton from "../../../../foundation/ui/buttons/RoutedButton";

function ListMessages() {
  const outletCtx = useAppHelpers();
  const params = useParams();
  const forwardEmailModalRef = useRef<ModalOpenState>(null);
  const [selectedItems, setSelectedItems] = useState<readonly Email[]>([]);
  const messages = useGetMessages(params?.folder_id);
  const message = useGetMessage(selectedItems[0]?.CaseID);
  const folder = useGetFolder(params?.folder_id);
  const { mutate, isPending: isExportMessagePending } = useExportMessage();
  const EmptyMessagePane =
    <Box variant="div" padding={{horizontal: 'xl', vertical: 'xxxl'}}>
      <Box variant="p" textAlign="center">Please, select an email message from the inbox first.</Box>
    </Box>
  const defaultPropertyQuery: PropertyFilterProps.Query = { tokens: [], operation: "or" };
  const getPropertyFilteringColumnConfig = (): PropertyFilterProps.FilteringProperty[] => {
    return [
      {
        key: "FromAddress",
        operators: ["=", "!=", ":", "!:"],
        propertyLabel: "From",
        groupValuesLabel: "From values"
      },
      {
        key: "EmailSubject",
        operators: ["=", "!=", ":", "!:"],
        propertyLabel: "Subject",
        groupValuesLabel: "Subject values"
      },
      {
        key: "RedactedBody",
        operators: ["=", "!=", ":", "!:"],
        propertyLabel: "Body",
        groupValuesLabel: "Body values"
      },
      {
        key: "DominantLanguage",
        operators: ["=", "!=", ":", "!:"],
        propertyLabel: "Primary Language",
        groupValuesLabel: "Primary Language values",
      },
      // {
      //   key: "date_sent",
      //   propertyLabel: "Send Date",
      //   groupValuesLabel: "Send Date values",
      //   operators: ["=", "!=", "<", "<=", ">", ">="].map(operator => ({
      //     operator,
      //     form: ({ value, onChange, filter }) => {
      //       if (typeof filter === "undefined") {
      //         return (
      //           <FormField>
      //             <DatePicker
      //               value={value ?? ""}
      //               onChange={event =>
      //                 onChange(event.detail.value)
      //               }
      //               placeholder="YYYY/MM/DD"
      //               locale="en-US"
      //             />
      //           </FormField>
      //         );
      //       }
      //       return (
      //         <div className="date-form">
      //           <FormField>
      //             <DateInput
      //               value={value ?? ""}
      //               onChange={event =>
      //                 onChange(event.detail.value)
      //               }
      //               placeholder="YYYY/MM/DD"
      //             />
      //           </FormField>
      //           <Calendar
      //             value={value ?? ""}
      //             onChange={event =>
      //               onChange(event.detail.value)
      //             }
      //             locale="en-US"
      //           />
      //         </div>
      //       );
      //     },
      //     match: "date"
      //   }))
      // }
    ];
  }

  const { items, actions, filteredItemsCount, /* collectionProps, */ /* filterProps,*/ propertyFilterProps/* , paginationProps */ } = useCollection(
    messages.data ?? [],
    {
      filtering: {
        empty:
          <EmptyState title="No emails are available" />,
        noMatch: (
          <EmptyState
            title="No matches"
            action={<Button onClick={() => actions.setFiltering('')}>Clear filter</Button>}
          />
        ),
      },
      propertyFiltering: {
        filteringProperties: getPropertyFilteringColumnConfig(),
        empty:
          <EmptyState
            title="No matches"
            action={<Button onClick={() => actions.setFiltering('')}>Clear filter</Button>}
          />
      },
      sorting: {
        defaultState: {
          sortingColumn: {
            sortingField: "EmailReceiveTime"
          },
          isDescending: true
        }
      },
      selection: {
        keepSelection: true
      },
    }
  );

  const handleSelectedItems = (selectedItems: readonly Email[] | undefined): void => {
    if (selectedItems) {
      // Converting from readonly to mutable array
      const items = selectedItems.concat();
      setSelectedItems(items);
    }
  }

  const getMessagePane = (content: ReactNode): AppLayoutProps.Drawer[] => {
    return [
      {
        id: "message",
        defaultSize: 750,
        resizable: true,
        content: content,
        trigger: { iconName: "envelope" },
        ariaLabels: {
          drawerName: "Email message",
          closeButton: "Close email message",
          triggerButton: "View email message",
          resizeHandle: "Resize email message pane",
        }
      }
    ];
  }

  useEffect(() => {
    outletCtx.setActiveDrawer(getMessagePane(EmptyMessagePane));
    outletCtx.setActiveDrawerId("message");
  }, []);

  useEffect(() => {
    // Set loading state
    if(selectedItems.length === 1) {
      message.refetch();
      outletCtx.setActiveDrawer(getMessagePane(<FullEmailDisplay email={message.data} isLoading={message.isLoading} onForwardEmail={() => forwardEmailModalRef.current?.setOpen(true)} />));
    }
  }, [selectedItems.length]);

  useEffect(() => {
    // Set loaded state
    if(message.data) {
      outletCtx.setActiveDrawer(getMessagePane(<FullEmailDisplay email={message.data} hasError={message.isError} onForwardEmail={() => forwardEmailModalRef.current?.setOpen(true)} />));
    }
  }, [message.data]);

  useEffect(() => {
    folder.refetch();
    messages.refetch();
    outletCtx.setActiveDrawer(getMessagePane(EmptyMessagePane));
    setSelectedItems([]);
  }, [params?.folder_id])

  return (
    <>
      {
        !(messages.isLoading || messages.isRefetching)
        ?
          <Header
            variant="h1"
            counter={`(${messages.data?.length ?? 0})`}
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Box>
                  <Button iconName="refresh" onClick={() => messages.refetch()} />
                </Box>
                <RoutedButton variant="normal" buttonText="Add Folder" href="/folders/create" onClick={() => {
                  outletCtx.setActiveDrawer([]);
                  outletCtx.setActiveDrawerId("");
                }} />
                {
                   (import.meta.env.VITE_EMAIL_ENABLED === "true") &&
                  <RoutedButton variant="normal" buttonText="Add Filtering Rule" href="/rules/create" onClick={() => {
                    outletCtx.setActiveDrawer([]);
                    outletCtx.setActiveDrawerId("");
                  }} />
                }
                {
                  messages.data && messages.data?.length > 0 &&
                  <Button variant="primary" iconName="download" disabled={isExportMessagePending} onClick={() => mutate({case_id: items?.map(message => message.CaseID) ?? []})}>Export</Button>
                }
              </SpaceBetween>
            }
          >
            { (folder.data) ? folder.data?.Name : "Inbox" }
          </Header>
        :
          <Spinner size="large" />
      }

      <Cards
        cardDefinition={{
          header: item => (
            <Header
              variant="h2"
              description={
                <>
                  <span>{ item.CaseID }</span><br />
                  <span>{ item.FromAddress }</span>
                </>
              }
            >
              { item.EmailSubject }
            </Header>
          ),
          sections: [
            { id: "DisplayedBody", content: item => (<EmailPreviewBody email={item} />) },
            { id: "RedactedBody", content: item => item.RedactedBody },
            { id: "EmailSubject", content: item => item.EmailSubject },
            { id: "FromAddress", content: item => item.FromAddress },
            { id: "DominantLanguage", content: item => item.DominantLanguage },
            // { id: "EmailReceiveTime", content: item => item.EmailReceiveTime },
          ]
        }}
        cardsPerRow={[
          { cards: 1 },
        ]}
        empty={
          <>
            <br /><br />
            <EmptyState title="No emails are available" />
          </>
        }
        entireCardClickable
        items={items}
        loading={messages.isLoading || messages.isRefetching}
        loadingText="Loading messages..."
        selectedItems={selectedItems}
        selectionType="single"
        stickyHeader
        totalItemsCount={messages.data?.length ?? 0}
        trackBy={"CaseID"}
        variant="full-page"
        visibleSections={[
          "DisplayedBody"
        ]}
        onSelectionChange={({detail}) => {
          handleSelectedItems(detail.selectedItems);
        }}

        filter={
          ((messages.data && messages.data?.length > 0) && !(messages.isLoading || messages.isRefetching)) &&
          <PropertyFilter
            {...propertyFilterProps}
            filteringPlaceholder="Find messages"
            countText={getMatchesCountText(filteredItemsCount ?? 0)}
            filteringAriaLabel="Filter messages"
            disableFreeTextFiltering={false}
            customFilterActions={
              <Button onClick={() => actions.setPropertyFiltering(defaultPropertyQuery)}>Clear filter(s)</Button>
            }
          />
        }
      />

      {
        (selectedItems.length === 1 && import.meta.env.VITE_EMAIL_ENABLED === "true") &&
        <ForwardEmail ref={forwardEmailModalRef} email={message.data!} />
      }
    </>
  )
}

export default ListMessages;
