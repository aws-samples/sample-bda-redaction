import axios from "axios";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { Folder } from "../../../foundation/folders/types";

type FolderFormValues = Omit<Folder, "ID" | "CreatedAt" | "Creator" | "MessagesCount" | "CreatedAt" | "MessagesCount">

const createFolder = async(folderData: FolderFormValues): Promise<FolderFormValues> => {
  const { data } = await axios.post("/folders", folderData);
  return data;
}

export const useCreateFolder = () => {
  const queryClient = useQueryClient();

  return useMutation<FolderFormValues, Error, FolderFormValues>({
    mutationFn: createFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["Folders"] });
    },
    onError: (error: any) => {
      console.error("Error creating folder:", error);
    }
  });
};