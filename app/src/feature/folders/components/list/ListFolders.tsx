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
import { useGetFolders } from "../../hooks/UseGetFolders";
import { useDeleteFolder } from "../../hooks/UseDeleteFolder";
import { useExportMessage } from "../../../email/hooks/UseExportMessages";
import { columnDefinitions, collectionPreferencesProps } from "../../../../foundation/folders/folder-config";
import { getVisibleColumns } from "../../../../foundation/ui/table/libs/helpers";
import { Folder } from "../../../../foundation/folders/types";
import { ModalOpenState } from "../../../../foundation/ui/types";
import { useAppHelpers } from "../../../../foundation/ui/layout/libs/helpers";

function ListFolders() {
  const { data, isLoading, isRefetching, refetch } = useGetFolders();
  const { mutate: deleteFolder, isPending } = useDeleteFolder();
  const { mutate } = useExportMessage();
  const navigate = useNavigate();
  const outletCtx = useAppHelpers();
  const [selectedItems, setSelectedItems] = useState<readonly Folder[]>([]);
  const deleteModalRef = useRef<ModalOpenState>(null);

  const handleActions = (detail: ButtonDropdownProps.ItemClickDetails) => {
    switch(detail.id) {
      case "export": {
        mutate({
          case_id: selectedItems.map(item => {
            return item.ID;
          })
        });
        break;
      }
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

  const handleSelectedItems = (selectedItems?: readonly Folder[]): void => {
    if(selectedItems) {
      // Converting from readonly to mutable array
      const items = selectedItems.concat();
      setSelectedItems(items);
    }
  }

  const deleteFolderAction = () => {
    deleteFolder(selectedItems[0]?.ID, {
      onSuccess: () => {
        outletCtx.setNotifications([
          {
            type: "success",
            header: "Success!",
            content: `Folder was deleted successfully`
          }
        ]);
      },
      onError: () => {
        outletCtx.setNotifications([
          {
            type: "error",
            header: "Error!",
            content: `Not able to delete folder`
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
        columnDisplay={getVisibleColumns(columnDefinitions)}
        items={data ?? []}
        loading={isLoading || isRefetching}
        selectionType="single"
        trackBy="ID"
        tableTitle="Folders"
        defaultSortingColumn="Name"
        isItemDisabled={(item) => item.ID === "general_inbox"}
        tableHeaderActions={
          <SpaceBetween direction="horizontal" size="xs">
            <RoutedButton
              buttonText="Create New Folder"
              variant="normal"
              href="/folders/create"
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
          <EmptyState title="Folders not available" />
        }
        collectionPreferencesProps={collectionPreferencesProps}
        excludePropertyFilteringFields={['CreatedAt']}
        emitSelectedItems={handleSelectedItems}
        refreshItems={refetch}
      />

      <DeleteModal
        ref={deleteModalRef}
        entityName={selectedItems[0]?.Name}
        entityType="folder"
        modalHeader="Delete Folder"
        formSubmitLoading={isPending}
        handleFormSubmit={deleteFolderAction}
      />
    </>
  )
}

export default ListFolders;