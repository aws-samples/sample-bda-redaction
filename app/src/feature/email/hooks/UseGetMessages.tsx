import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import { Email } from "../../../foundation/email/types";

const getMessages = async(): Promise<Email[]> => {
  const response = await axios.get(`/messages`, {withCredentials: false});
  return response.data;
}

export const useGetMessages = () => {
  return useQuery<Email[], Error>({
    queryKey: ['Messages'],
    queryFn: () => getMessages(),
    retry: false,
  });
};