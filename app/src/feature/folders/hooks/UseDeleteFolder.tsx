import axios from "axios";
import { useQueryClient, useMutation } from "@tanstack/react-query";

const deleteFolder = async(folder_id: string): Promise<string> => {
  const { data } = await axios.delete(`/folders/${folder_id}`);
  return data;
}

export const useDeleteFolder = () => {
  const queryClient = useQueryClient();

  return useMutation<string, Error, string>({
    mutationFn: deleteFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["Folders"] });
    },
    onError: (error: any) => {
      console.error("Error deleting folder:", error);
    }
  });
};