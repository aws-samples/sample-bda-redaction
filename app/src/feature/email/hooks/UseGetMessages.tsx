import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import { Email } from "../../../foundation/email/types";

const getMessages = async(folder_id?: string): Promise<Email[]> => {
  const response = (folder_id) ? await axios.get(`/folders/${folder_id}/messages`) : await axios.get(`/messages`, {withCredentials: false});
  return response.data;
}

export const useGetMessages = (folder_id?: string) => {
  return useQuery<Email[], Error>({
    queryKey: ['Messages'],
    queryFn: () => getMessages(folder_id),
    retry: false,
  });
};