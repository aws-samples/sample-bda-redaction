import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import { Email } from "../../../foundation/email/types";

const getMessage = async(case_id: string): Promise<Email> => {
  const { data } = await axios.get(`/messages/${case_id}`);
  return data;
}

export const useGetMessage = (case_id: string) => {
  return useQuery<Email, Error>({
    queryKey: [`Message-${case_id}`],
    queryFn: () => getMessage(case_id),
    retry: false,
    enabled: !!case_id,
    gcTime: 0,
  });
};