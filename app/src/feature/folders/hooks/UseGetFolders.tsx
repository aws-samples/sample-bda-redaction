import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import { Folder } from "../../../foundation/folders/types";

const getFolders = async(): Promise<Folder[]> => {
  const { data } = await axios.get("/folders");
  return data;
}

export const useGetFolders = () => {
  return useQuery<Folder[], Error>({
    queryKey: ['Folders'],
    queryFn: getFolders,
    retry: false
  });
};