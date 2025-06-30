import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import { Folder } from "../../../foundation/folders/types";

const getFolder = async(folder_id?: string): Promise<Folder|null> => {
  try {
    let folder = folder_id;

    if (!folder) {
      folder = 'general_inbox';
    }

    const { data } = await axios.get(`/folders/${folder}`);
    return data;
  } catch (error) {
    console.error(error);
    return null;
  }
}

export const useGetFolder = (folder_id?: string) => {
  return useQuery<Folder|null, Error>({
    queryKey: ['Folder'],
    queryFn: () => getFolder(folder_id),
    retry: false,
    enabled: true,
  });
};