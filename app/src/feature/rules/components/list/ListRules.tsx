import { useRef, useState, useEffect } from "react";
import {
  ButtonDropdown,
  ButtonDropdownProps,
  SpaceBetween
} from "@cloudscape-design/components";
import { useNavigate } from "react-router-dom";
import DataTable from "../../../../foundation/ui/table/components/DataTable";
import EmptyState from "../../../../foundation/ui/table/components/EmptyState";
import RoutedButton from "../../../../foundation/ui/buttons/RoutedButton";
import DeleteModal from "../../../../foundation/ui/form/components/DeleteModal";
import { useGetRules } from "../../hooks/UseGetRules";
import { useDeleteRule } from "../../hooks/UseDeleteRule";
// import { useToggleRule } from "../../hooks/UseToggleRule";
import { columnDefinitions, collectionPreferencesProps } from "../../../../foundation/rules/rule-config";
import { Rule } from "../../../../foundation/rules/types";
import { ModalOpenState } from "../../../../foundation/ui/types";
import { useAppHelpers } from "../../../../foundation/ui/layout/libs/helpers";

function ListRules() {
  const { data, isLoading, isRefetching, refetch } = useGetRules();
  const { mutate: deleteRule, isPending } = useDeleteRule();
  // const toggleRule = useToggleRule();
  const navigate = useNavigate();
  const outletCtx = useAppHelpers();
  const [selectedItems, setSelectedItems] = useState<readonly Rule[]>([]);
  const deleteModalRef = useRef<ModalOpenState>(null);

  const handleActions = (detail: ButtonDropdownProps.ItemClickDetails) => {
    switch(detail.id) {
      case "delete": {
        deleteModalRef.current?.setOpen(true);
        break;
      }
      default:
        if(detail.href) {
          navigate(detail.href, { replace: true });
        }
        break;
    }
  }

  const handleSelectedItems = (selectedItems?: readonly Rule[]): void => {
    if(selectedItems) {
      // Converting from readonly to mutable array
      const items = selectedItems.concat();
      setSelectedItems(items);
    }
  }

  // const toggleRuleAction = (rule: Rule) => {
  //   toggleRule.mutate({
  //     rule_id: rule.ID,
  //     enabled: !rule.Enabled
  //   },
  //   {
  //     onSuccess: () => {
  //       outletCtx.setNotifications([
  //         {
  //           type: "success",
  //           header: "Success!",
  //           content: `Rule '${rule.Description}' enabled status changed to ${(rule.Enabled ? 'No' : 'Yes')}`
  //         }
  //       ]);
  //       refetch();
  //     },
  //     onError: () => {
  //       outletCtx.setNotifications([
  //         {
  //           type: "error",
  //           header: "Error!",
  //           content: `Not able to change status of rule '${rule.Description}'`
  //         }
  //       ]);
  //     }
  //   });
  // }

  const deleteRuleAction = () => {
    deleteRule(selectedItems[0].ID, {
      onSuccess: () => {
        outletCtx.setNotifications([
          {
            type: "success",
            header: "Success!",
            content: `Rule was deleted successfully`
          }
        ]);
      },
      onError: () => {
        outletCtx.setNotifications([
          {
            type: "error",
            header: "Error!",
            content: `Not able to delete rule`
          }
        ]);
      },
      onSettled: () => {
        deleteModalRef.current?.setOpen(false);
        refetch();
      }
    })
  }

  useEffect(() => {
    outletCtx.setActiveDrawerId("");
    outletCtx.setActiveDrawer([]);
  }, []);

  return (
    <>
      <DataTable
        columnDefinitions={columnDefinitions}
        items={data ?? []}
        loading={isLoading || isRefetching}
        selectionType="single"
        trackBy="ID"
        tableTitle="Email Filtering Rules"
        defaultSortingColumn="ID"
        tableHeaderActions={
          <SpaceBetween direction="horizontal" size="xs">
            <RoutedButton
              buttonText="Create New Rule"
              variant="normal"
              href="/rules/create"
            />
            <ButtonDropdown
              variant="primary"
              onItemClick={(e) => {
                e.preventDefault();
                handleActions(e.detail);
              }}
              expandToViewport={true}
              items={[
                { text: "Delete", id: "delete", disabled: !(selectedItems?.length === 1) },
              ]}
            >
              Actions
            </ButtonDropdown>
          </SpaceBetween>
        }
        empty={
          <EmptyState title="Rules not available" />
        }
        collectionPreferencesProps={collectionPreferencesProps}
        excludePropertyFilteringFields={['CreatedAt']}
        // customColumnActions={{
        //   "toggle": {
        //     eventAction: (item: Rule) => toggleRuleAction(item),
        //     buttonLabel: "Enable/Disable"
        //   }
        // }}
        emitSelectedItems={handleSelectedItems}
        refreshItems={refetch}
      />

      <DeleteModal
        ref={deleteModalRef}
        entityName={selectedItems[0]?.Description}
        entityType="rule"
        modalHeader="Delete Rule"
        formSubmitLoading={isPending}
        handleFormSubmit={deleteRuleAction}
      />
    </>
  )
}

export default ListRules;